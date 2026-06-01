# ICASHTL Deployment Guide

This guide covers everything needed to go from a clean checkout to a published
monthly release: environment setup, pipeline execution, bundle generation,
R2 artifact upload, GitHub release tagging, buyer delivery, and Cloudflare Pages
deployment. It assumes familiarity with the pipeline (see `runbook.md`) but not
with the infrastructure.

---

## 1. Prerequisites

### Local tools

| Tool | Install | Verify |
|---|---|---|
| Python 3.11+ | `brew install python@3.12` | `python3 --version` |
| Dolt | `brew install dolt` | `dolt version` |
| Playwright Chromium | `playwright install chromium` | `playwright --version` |
| boto3 (R2 uploads) | `pip install boto3` | `python3 -c "import boto3"` |
| git | pre-installed on macOS | `git --version` |

Install all Python dependencies:

```bash
pip install -r requirements.txt
```

### Cloudflare R2 bucket

1. Log in to [dash.cloudflare.com](https://dash.cloudflare.com) → **R2** → **Create bucket**.
2. Name the bucket `icashtl-releases` (or update `r2.bucket_env` in `pipelines/publish/config.yaml`).
3. Go to **R2 → Manage R2 API Tokens** → **Create API Token** with *Object Read & Write* on that bucket.
4. Note the **Account ID** (visible in the R2 overview URL) — it appears in the endpoint URL.

### Environment variables

Copy `.env.example` to `.env` in the project root and fill in R2 credentials:

```bash
cp .env.example .env
```

```bash
# .env
R2_BUCKET=icashtl-releases
R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=<your-access-key>
R2_SECRET_ACCESS_KEY=<your-secret-key>
```

Load them before running any upload steps:

```bash
export $(grep -v '^#' .env | xargs)
```

### Dolt identity (one-time)

```bash
dolt config --global --add user.name  "Your Name"
dolt config --global --add user.email "you@example.com"
```

### First-time Dolt schema init (fresh clone only)

```bash
cd dolt/
dolt sql < schema.sql
dolt sql < seed_corporate_actions.sql
dolt add --all
dolt commit -m "Initial schema"
cd ..
```

---

## 2. Full Pipeline Run

Run the complete pipeline for the release date:

```bash
python3 pipelines/run.py --date 2026-06-01
```

This executes all nine tasks in order:

| Task | What it does |
|---|---|
| `extract` | Downloads NSE equity master, bhavcopy, and corporate actions |
| `normalize` | Maps raw fields to canonical schemas → `data/curated/` |
| `lineage` | Builds symbol lineage events |
| `adjust` | Calculates adjustment factors for splits and bonuses |
| `validate` | Runs 6 data quality checks (must all pass before Dolt commit) |
| `load` | Imports curated CSVs into Dolt and commits |
| `export` | Generates public sample and paid-tier Parquet exports |
| `manifest` | Writes `data/samples/metadata/manifest_YYYYMMDD.md` |
| `release-notes` | Drafts `releases/monthly/vYYYY.MM.DD.md` |

A successful run ends with:

```
Pipeline completed successfully for 2026-06-01
```

### Partial and diagnostic runs

```bash
# Skip NSE download (use existing raw files)
python3 pipelines/run.py --no-fetch --tasks normalize,lineage,adjust,validate

# Skip Dolt commit and R2 (safe to run repeatedly)
python3 pipelines/run.py --dry-run

# Re-run only failed stages
python3 pipelines/run.py --no-fetch --tasks validate,load
```

### Non-fatal warnings

The following warnings are expected and do not block a release:

- **Bhavcopy 404** — no bhavcopy on weekends or public holidays. Non-fatal.
- **Corporate actions 0 rows** — NSE API may be rate-limiting or unreachable
  from the current machine. Run from a server or VPN, or retry the next business
  day. Validate will pass with a warning; the release proceeds without adjustment
  factors.
- **Bhavcopy stale** — the most recent cached bhavcopy is older than today.
  EOD prices in this release are from the last cached date.

---

## 3. Build Delivery Bundles

After a successful pipeline run, generate the per-tier zip bundles:

```bash
python3 - <<'EOF'
from pipelines.publish.packager import BundlePackager
from datetime import date

p = BundlePackager()
run_date = date(2026, 6, 1)   # set to the release date

for tier in p.list_tiers():
    path = p.build_bundle(tier, run_date)
    print(f"{tier:14s}  →  {path}")
EOF
```

Bundles are written to `releases/bundles/`:

```
releases/bundles/
  icashtl_explorer_20260601.zip       ← free tier
  icashtl_starter_20260601.zip        ← Starter (paid)
  icashtl_professional_20260601.zip   ← Professional (paid)
  icashtl_enterprise_20260601.zip     ← Enterprise (paid)
```

Each zip contains: data files for the tier, `LICENSE.md`, `README.md`,
`sample_queries.sql`, and `MANIFEST.json` with row counts and checksums.

---

## 4. Upload Artifacts to Cloudflare R2

### Manual upload (local machine)

Load `.env` first, then:

```bash
python3 - <<'EOF'
import boto3, os
from pathlib import Path

s3 = boto3.client(
    "s3",
    endpoint_url=os.environ["R2_ENDPOINT"],
    aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
)
bucket   = os.environ["R2_BUCKET"]
run_date = "2026-06-01"   # set to release date

# Upload paid-tier sample exports
for tier in ["paid_tier_1", "paid_tier_2"]:
    for path in Path(f"data/samples/{tier}").glob("*"):
        key = f"releases/{run_date}/{tier}/{path.name}"
        s3.upload_file(str(path), bucket, key)
        print(f"Uploaded  {key}")

# Upload release bundles
for path in Path("releases/bundles").glob(f"*{run_date.replace('-', '')}*"):
    key = f"releases/{run_date}/bundles/{path.name}"
    s3.upload_file(str(path), bucket, key)
    print(f"Uploaded  {key}")
EOF
```

Verify the uploads:

```bash
python3 - <<'EOF'
import boto3, os
s3 = boto3.client("s3", endpoint_url=os.environ["R2_ENDPOINT"],
                  aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                  aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"])
resp = s3.list_objects_v2(Bucket=os.environ["R2_BUCKET"], Prefix="releases/2026-06-01/")
for obj in resp.get("Contents", []):
    print(f"{obj['Size']:>10}  {obj['Key']}")
EOF
```

### Automated upload via GitHub Actions

The `release.yml` workflow uploads paid-tier exports automatically when a tag
is pushed. See Section 6 below.

---

## 5. Generate Buyer Signed URLs

When a buyer is onboarded, generate a 7-day pre-signed R2 download URL:

```bash
python3 - <<'EOF'
from pipelines.publish.access_manager import AccessManager

mgr = AccessManager()

# Register a new buyer (first time only)
buyer = mgr.create_buyer(
    name="Acme Capital",
    email="data@acmecapital.in",
    tier="starter",
)
print("buyer_id:", buyer["buyer_id"])

# Generate a signed download URL for their bundle
s3_key = "releases/2026-06-01/bundles/icashtl_starter_20260601.zip"
url = mgr.generate_signed_url(buyer["buyer_id"], s3_key)
print("Download URL (valid 7 days):")
print(url)
EOF
```

Buyer records are stored in `data/buyers/buyers.csv`. Download activity is
logged to `data/buyers/download_log.csv`. Neither file should be committed to git.

Send the URL directly to the buyer — no other delivery infrastructure is needed
for the MVP.

---

## 6. GitHub Release Tag

Pushing a version tag triggers `release.yml`, which:
1. Runs `export`, `manifest`, and `release-notes` tasks.
2. Creates a GitHub Release with the release notes as the description.
3. Attaches the public sample CSV and manifest as release assets.
4. Uploads paid-tier Parquet files to R2 (if secrets are configured).

Tag format: `v<YYYY>.<MM>.<DD>` matching the run date.

```bash
git tag v2026.06.01
git push origin v2026.06.01
```

To confirm the workflow ran: **GitHub → Actions → Release**.

### GitHub Actions secrets required

Set these under **GitHub → Repository → Settings → Secrets and variables → Actions**:

| Secret | Value |
|---|---|
| `R2_BUCKET` | `icashtl-releases` |
| `R2_ENDPOINT` | `https://<account-id>.r2.cloudflarestorage.com` |
| `R2_ACCESS_KEY_ID` | R2 API token access key |
| `R2_SECRET_ACCESS_KEY` | R2 API token secret |

Without these secrets the workflow still creates the GitHub Release; only the
R2 upload step is skipped.

---

## 7. Nightly Automation

The `nightly.yml` workflow runs Mon–Fri at 2:00 AM IST (20:30 UTC previous day).
It runs the full pipeline, commits to Dolt, and uploads exports to R2.

To trigger a one-off run manually:

1. Go to **GitHub → Actions → Nightly Data Refresh**.
2. Click **Run workflow**.
3. Optionally set `run_date` (defaults to today) and `dry_run`.

If the nightly run fails, GitHub emails the repository owner. Check the Actions
log for which task failed, fix the root cause, and re-run the affected tasks
locally or via workflow dispatch.

---

## 8. Cloudflare Pages (Public Site)

The `website/` directory contains the landing page and public docs. It is
deployed to Cloudflare Pages.

### First-time Pages setup

1. Go to [dash.cloudflare.com](https://dash.cloudflare.com) → **Pages** → **Create a project**.
2. Connect to the GitHub repository.
3. Set:
   - **Framework preset:** None
   - **Build command:** *(leave blank — static site — Cloudflare may auto-populate this from `requirements.txt`; delete whatever it suggests)*
   - **Build output directory:** `website/landing-page`
4. Click **Save and Deploy**.

> **Common failure:** if the build log shows `pip install -r requirements.txt` running, Cloudflare auto-detected the repo's Python dependencies and added them as a build step. Clear the Build command field and redeploy — the site is static HTML and needs no build step.

Subsequent pushes to `main` redeploy automatically.

### Manual deploy (without GitHub integration)

```bash
# Install Wrangler (Cloudflare's CLI)
npm install -g wrangler

# Authenticate
wrangler login

# Deploy
wrangler pages deploy website/landing-page --project-name icashtl
```

### Updating public docs

The `website/landing-page/` files mirror `docs/`. To sync after editing docs:

```bash
# Copy updated docs into the website (only the subscriber-facing ones)
cp docs/product-overview.md website/landing-page/
cp docs/methodology.md      website/landing-page/
cp docs/pricing.md          website/landing-page/
cp docs/sample-queries.md   website/landing-page/
```

Then commit and push — Pages redeploys automatically.

---

## 9. End-to-End Release Checklist

Use this checklist before tagging each monthly release:

- [ ] `python3 pipelines/run.py --date <YYYY-MM-DD>` exits 0
- [ ] `python3 pipelines/run.py --tasks validate` exits 0
- [ ] `data/curated/dim_security_master.csv` has ≥ 2,000 rows
- [ ] `releases/monthly/v<YYYY.MM.DD>.md` exists and is non-empty
- [ ] `data/samples/public/nse_active_securities_sample_*.csv` is non-empty
- [ ] Bundles built for all tiers (Section 3)
- [ ] R2 upload confirmed (Section 4)
- [ ] Release notes reviewed in `releases/monthly/v<YYYY.MM.DD>.md`
- [ ] `git tag v<YYYY.MM.DD> && git push origin v<YYYY.MM.DD>` — GitHub Release created
- [ ] Paid-tier buyers notified with new signed URLs (Section 5)

---

## 10. Rollback

### Revert a bad Dolt commit

```bash
cd dolt/
dolt log --oneline | head -5        # find last good commit hash
dolt reset --hard <hash>
# Then re-run load with corrected data:
python3 pipelines/run.py --no-fetch --tasks load
```

### Delete a GitHub Release

```bash
gh release delete v2026.06.01 --yes
git tag -d v2026.06.01
git push origin :refs/tags/v2026.06.01
```

### Remove an R2 upload

```bash
python3 - <<'EOF'
import boto3, os
s3 = boto3.client("s3", endpoint_url=os.environ["R2_ENDPOINT"],
                  aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                  aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"])
# List objects to confirm before deleting
resp = s3.list_objects_v2(Bucket=os.environ["R2_BUCKET"], Prefix="releases/2026-06-01/")
for obj in resp.get("Contents", []):
    s3.delete_object(Bucket=os.environ["R2_BUCKET"], Key=obj["Key"])
    print(f"Deleted  {obj['Key']}")
EOF
```

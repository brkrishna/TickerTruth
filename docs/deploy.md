# TickerTruth Deployment Guide

This guide covers everything needed to go from a clean checkout to a published
monthly release: environment setup, pipeline execution, bundle generation,
R2 artifact upload, GitHub release tagging, buyer delivery, and Cloudflare Workers
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
2. Name the bucket `tickertruth-releases` (or update `r2.bucket_env` in `pipelines/publish/config.yaml`).
3. Go to **R2 → Manage R2 API Tokens** → **Create API Token** with *Object Read & Write* on that bucket.
4. Note the **Account ID** (visible in the R2 overview URL) — it appears in the endpoint URL.

### Environment variables

Copy `.env.example` to `.env` in the project root and fill in R2 credentials:

```bash
cp .env.example .env
```

```bash
# .env
R2_BUCKET=tickertruth-releases
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
  tickertruth_explorer_20260601.zip       ← free tier
  tickertruth_starter_20260601.zip        ← Starter (paid)
  tickertruth_professional_20260601.zip   ← Professional (paid)
  tickertruth_enterprise_20260601.zip     ← Enterprise (paid)
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

### Automated upload

There is no `release.yml` workflow anymore (removed — see Section 6). Run the
upload script above manually after each release, or write a replacement
automation if you want this hands-off again.

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
s3_key = "releases/2026-06-01/bundles/tickertruth_starter_20260601.zip"
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

## 6. GitHub Release Tag (manual — `release.yml` removed)

`release.yml` used to run this automatically on a version tag push. It was
removed (2026-09-05) along with `nightly.yml`; both were unrelated to the
website's Pages→Workers migration but were dropped in the same pass. Run
the equivalent steps by hand for each release:

```bash
python pipelines/run.py --date <YYYY-MM-DD> \
  --tasks export,manifest,release-notes,website \
  --no-fetch --no-dolt-commit

git tag v2026.06.01
git push origin v2026.06.01

gh release create v2026.06.01 \
  --title "Release v2026.06.01" \
  --notes-file releases/monthly/v2026.06.01.md \
  data/samples/public/*.csv data/samples/public/*.sha256 data/samples/metadata/manifest_*.md
```

Then upload paid-tier artifacts to R2 using the script in Section 4 above.
Commit the updated `website/public/release-notes.html` and
`releases/monthly/<tag>.md` to `main` yourself — there is no bot pushing
this back anymore.

---

## 7. Nightly Data Refresh (manual — `nightly.yml` removed)

`nightly.yml` used to run the extract → normalize → lineage → adjust →
validate → load pipeline Mon–Fri at 2:00 AM IST and push Dolt state to this
repo. That automation no longer runs. Refresh data by running the pipeline
yourself:

```bash
python pipelines/run.py --tasks extract,normalize,lineage,adjust,validate,load
cd dolt && dolt push origin main
```

If you want this hands-off again, either restore `nightly.yml` from git
history (`git log -- .github/workflows/nightly.yml`) or write a replacement
scheduler. If a run fails, fix the root cause and re-run the affected tasks
locally.

---

## 8. Cloudflare Workers (Public Site)

The `website/public/` directory contains the landing page and public docs.
It is deployed as static assets on a Cloudflare Worker (`src/index.js` also
handles `/api/contact` and `/api/razorpay-webhook`). Config lives in
`wrangler.jsonc` at the repo root.

### First-time Workers setup (done — recorded for reference)

```bash
# Install dependencies (wrangler, eslint, vitest, playwright)
npm install

# Authenticate
npx wrangler login

# Deploy — creates the Worker project on first run
npx wrangler deploy
```

Secrets (set once, or after rotating them):

```bash
npx wrangler secret put RESEND_API_KEY
npx wrangler secret put RAZORPAY_WEBHOOK_SECRET
```

The `tickertruth.com` custom domain is mapped to the Worker from
**dash.cloudflare.com → Workers & Pages → tickertruth → Settings → Domains & Routes**,
and the Worker is git-connected (Workers Builds) to this repo — pushing to
`main` triggers an automatic build + deploy.

### Redeploying — the Hugo blog is a committed artifact, not a build step

**Cloudflare's Workers Builds environment does not have Hugo installed.**
`website/public/blog/` is therefore committed to git (unlike the old Pages
build, which had a `HUGO_VERSION` buildpack) — Cloudflare's auto-deploy just
uploads whatever is already in `website/public/`. If you edit anything under
`website/blog/` (a new post, template change, etc.) you must rebuild and
commit the output yourself, or the live site won't reflect it:

```bash
hugo --source website/blog --destination ../public/blog --minify
git add website/public/blog
git commit -m "blog: rebuild"
git push origin main   # triggers the Cloudflare build + deploy
```

Everything else under `website/public/` (pricing.html, methodology.html,
etc.) is already committed directly — just edit and push.

To deploy from your machine instead of waiting on Cloudflare's build:

```bash
npx wrangler deploy
```

### Updating public docs

The `website/public/` files mirror `docs/`. To sync after editing docs:

```bash
# Copy updated docs into the website (only the subscriber-facing ones)
cp docs/product-overview.md website/public/
cp docs/methodology.md      website/public/
cp docs/pricing.md          website/public/
cp docs/sample-queries.md   website/public/
```

Then commit, and redeploy per the steps above.

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

# Buyer Onboarding Guide

Manual commercial onboarding process for TickerTruth data subscribers.
All steps are performed by the operator until automated fulfillment is added.

---

## 1. Receiving a New Inquiry

Buyers reach out via:
- Website contact form (contact@tickertruth.com)
- LinkedIn / X DM
- Word of mouth

**Response SLA:** 24 hours.

Initial reply template:

> Thanks for your interest in TickerTruth. We provide versioned NSE symbol
> lineage and corporate action data for backtesting and analytics.
>
> Could you share:
> 1. Your use case (backtesting / research / production system)?
> 2. The date range and coverage you need?
> 3. Your preferred delivery format (CSV or Parquet)?
>
> I'll send you a sample (Explorer tier, free) so you can evaluate the
> data quality before committing.

---

## 2. Sending the Explorer Sample

```bash
# Build the Explorer bundle for today
python pipelines/run.py --tasks export
python -c "
from pipelines.publish.packager import BundlePackager
from datetime import date
BundlePackager().build_bundle('explorer', date.today())
"
# Bundle is in releases/bundles/tickertruth_explorer_{date}.zip
```

Send the zip directly via email. No signed URL needed for the free tier.

---

## 3. Creating a Buyer Record

Once the buyer confirms they want to subscribe:

```bash
python -c "
from pipelines.publish.access_manager import AccessManager
mgr = AccessManager()
buyer = mgr.create_buyer(
    name  = 'Acme Quant Pvt Ltd',
    email = 'data@acmequant.in',
    tier  = 'starter',
    notes = 'INR 25000/month, payment ref TXN-20260601',
)
print('Buyer ID:', buyer['buyer_id'])
"
```

Record the buyer_id — you'll need it for every access operation.

---

## 4. Payment Collection

**Current method:** Manual bank transfer or Razorpay payment link.

1. Send invoice with payment details (bank account or Razorpay link).
2. Confirm receipt and update buyer notes:

```bash
python -c "
from pipelines.publish.access_manager import AccessManager
mgr    = AccessManager()
buyers = mgr.list_buyers()
# Edit buyers.csv directly to update notes:
# notes: 'Payment confirmed TXN-20260601, invoice INV-001'
"
# Or edit data/buyers/buyers.csv directly.
```

**Planned:** Razorpay webhook integration in Phase 6.

---

## 5. Delivering the Bundle

### Step 1 — Build the bundle

```bash
python -c "
from pipelines.publish.packager import BundlePackager
from datetime import date
path = BundlePackager().build_bundle('starter', date.today())
print('Bundle:', path)
"
```

### Step 2 — Upload to R2

```bash
# Set R2 credentials in environment or .env
export R2_BUCKET=tickertruth-releases
export R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
export R2_ACCESS_KEY_ID=<key>
export R2_SECRET_ACCESS_KEY=<secret>

python -c "
import boto3, os
from pathlib import Path

s3      = boto3.client('s3', endpoint_url=os.environ['R2_ENDPOINT'],
                       aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
                       aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'])
bundle  = Path('releases/bundles/tickertruth_starter_20260601.zip')
key     = f'releases/2026-06-01/starter/{bundle.name}'
s3.upload_file(str(bundle), os.environ['R2_BUCKET'], key)
print('Uploaded:', key)
"
```

### Step 3 — Generate signed URL (7-day expiry)

```bash
python -c "
from pipelines.publish.access_manager import AccessManager
mgr = AccessManager()
url = mgr.generate_signed_url(
    buyer_id = 'ABCD1234',   # from step 3
    s3_key   = 'releases/2026-06-01/starter/tickertruth_starter_20260601.zip',
)
print('Download URL:', url)
"
```

### Step 4 — Email the buyer

Subject: *Your TickerTruth Starter download is ready*

> Hi [Name],
>
> Your TickerTruth Starter bundle for 2026-06 is ready for download:
>
> [signed URL]
>
> This link expires in 7 days. If you need a new link, reply to this email.
>
> Please verify the download:
> ```
> sha256sum tickertruth_starter_20260601.zip
> ```
> Expected checksum is in MANIFEST.json inside the zip.
>
> Questions? Reply here or email contact@tickertruth.com.

---

## 6. Monthly Renewal Delivery

For active subscribers, the nightly pipeline generates fresh exports automatically.
Monthly re-delivery:

```bash
# 1. Build and upload
python pipelines/run.py --tasks export,manifest

# 2. Generate signed URLs for all active buyers of a tier
python -c "
from pipelines.publish.access_manager import AccessManager
from datetime import date

mgr     = AccessManager()
buyers  = mgr.list_buyers(tier='starter')
run_date = date.today().strftime('%Y%m%d')
key_template = 'releases/{date}/starter/tickertruth_starter_{date}.zip'

for buyer in buyers:
    key = key_template.format(date=run_date)
    url = mgr.generate_signed_url(buyer['buyer_id'], key)
    print(f\"{buyer['email']}: {url}\")
"
# Copy-paste URLs and send renewal emails.
```

---

## 7. Access Revocation

When a subscription lapses or is cancelled:

```bash
python -c "
from pipelines.publish.access_manager import AccessManager
mgr = AccessManager()
mgr.deactivate_buyer('ABCD1234')
print('Buyer deactivated')
"
```

Deactivated buyers are retained in `buyers.csv` for audit purposes (status = inactive).
Previously generated signed URLs will expire naturally within 7 days.

---

## 8. Audit Trail

All download URL generation is logged in `data/buyers/download_log.csv`.

```bash
# View recent downloads
python -c "
from pipelines.publish.access_manager import AccessManager
import pandas as pd
log = pd.read_csv('data/buyers/download_log.csv')
print(log.sort_values('generated_at').tail(10).to_string())
"
```

---

## 9. Escalation Contacts

| Issue | Contact |
|---|---|
| Data quality dispute | Review `_quality_issues` column in curated CSVs |
| Payment dispute | Check `data/buyers/buyers.csv` notes field |
| R2 access problem | Check R2 credentials in `.env` and Cloudflare dashboard |
| Dolt data issue | Run `python pipelines/run.py --tasks validate` |

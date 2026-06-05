# Publishing the TickerTruth Dataset to HuggingFace

The `releases/huggingface/` folder already contains the dataset card README and both data files. These steps cover the one-time org/repo setup and the upload process.

---

## Step 1 — Create the HuggingFace organization

1. Go to [huggingface.co](https://huggingface.co) → sign in (or create an account)
2. Click your avatar → **New Organization**
3. Name it exactly **`tickertruth`** (lowercase) — this matches what the README already references: `tickertruthorg/nse-india-security-master`
4. Set visibility to **Public**

---

## Step 2 — Create the dataset repository

1. On your org page, click **New Dataset**
2. Name: `nse-india-security-master`
3. License: **CC BY 4.0** (matches the dataset card)
4. Visibility: **Public**
5. Click **Create dataset** — don't add any files yet

---

## Step 3 — Install `huggingface_hub` and authenticate

```bash
pip install huggingface_hub
huggingface-cli login
```

Get your token at: **huggingface.co → Settings → Access Tokens → New token** (role: **Write**).

---

## Step 4 — Push the dataset

Run this from the repo root:

```bash
python - <<'EOF'
from huggingface_hub import HfApi

api = HfApi()

# Create repo if it doesn't exist yet (safe to re-run)
api.create_repo(
    repo_id="tickertruthorg/nse-india-security-master",
    repo_type="dataset",
    exist_ok=True,
    private=False,
)

# Upload the dataset card
api.upload_file(
    path_or_fileobj="releases/huggingface/README.md",
    path_in_repo="README.md",
    repo_id="tickertruthorg/nse-india-security-master",
    repo_type="dataset",
)

# Upload both data files
api.upload_file(
    path_or_fileobj="releases/huggingface/data/nse_security_master.csv",
    path_in_repo="data/nse_security_master.csv",
    repo_id="tickertruthorg/nse-india-security-master",
    repo_type="dataset",
)

api.upload_file(
    path_or_fileobj="releases/huggingface/data/nse_explorer_20symbols.csv",
    path_in_repo="data/nse_explorer_20symbols.csv",
    repo_id="tickertruthorg/nse-india-security-master",
    repo_type="dataset",
)

print("Done — https://huggingface.co/datasets/tickertruthorg/nse-india-security-master")
EOF
```

---

## Step 5 — Verify the published card

Visit `huggingface.co/datasets/tickertruthorg/nse-india-security-master` and check:

- The YAML tags render correctly (Finance, India, NSE badges appear)
- The **Files** tab shows `data/nse_security_master.csv` and `data/nse_explorer_20symbols.csv`
- The data viewer preview loads (HF auto-previews CSV files in the browser)

---

## Step 6 — Add the dataset link to tickertruth.com

Add a "Dataset" link in the nav and landing page pointing to the HuggingFace URL. This drives cross-traffic and gives the product social proof.

---

## Step 7 — Nightly auto-update (future)

When the nightly pipeline runs, add a publish step to `pipelines/publish/` that calls `api.upload_file(...)` for the refreshed `nse_security_master.csv`. The dataset card's "Updates nightly" claim will then be accurate.

---

## Checklist

- [ ] Create `tickertruth` org on HuggingFace
- [ ] Create `nse-india-security-master` dataset repo
- [ ] `pip install huggingface_hub` + `huggingface-cli login`
- [ ] Run the upload script above from the repo root
- [ ] Verify the card renders and data preview works
- [ ] Link back from tickertruth.com

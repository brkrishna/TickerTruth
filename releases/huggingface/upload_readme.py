"""
One-off script to push the dataset card README to HuggingFace.
Run from the repo root:
    HF_TOKEN=hf_... python3 releases/huggingface/upload_readme.py
"""

import os
import sys
from pathlib import Path

from huggingface_hub import HfApi

REPO_ID = "tickertruthorg/nse-india-security-master"
README = Path(__file__).parent / "README.md"

token = os.environ.get("HF_TOKEN", "").strip()
if not token:
    print("Error: HF_TOKEN not set.")
    print("Run: export HF_TOKEN=hf_your_token_here")
    sys.exit(1)

api = HfApi(token=token)

DATA_DIR = Path(__file__).parent / "data"
IMAGES_DIR = Path(__file__).parent / "images"

api.upload_folder(
    folder_path=str(Path(__file__).parent),
    repo_id=REPO_ID,
    repo_type="dataset",
    allow_patterns=["README.md", "data/*.csv", "images/*"],
    commit_message="upload dataset card, data files, and images",
)
print(f"Done — https://huggingface.co/datasets/{REPO_ID}")

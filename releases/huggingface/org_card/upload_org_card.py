"""
Creates the tickertruthorg org card on HuggingFace.

HuggingFace org cards are static Spaces named "README" under the org:
  tickertruthorg/README

Run from the repo root:
    HF_TOKEN=hf_... python3 releases/huggingface/org_card/upload_org_card.py
"""

import os
import sys
from pathlib import Path

from huggingface_hub import HfApi

REPO_ID = "tickertruthorg/README"
ORG_CARD_DIR = Path(__file__).parent

token = os.environ.get("HF_TOKEN", "").strip()
if not token:
    print("Error: HF_TOKEN not set.")
    print("Run: export HF_TOKEN=hf_your_token_here")
    sys.exit(1)

api = HfApi(token=token)

api.create_repo(
    repo_id=REPO_ID,
    repo_type="space",
    space_sdk="static",
    exist_ok=True,
    private=False,
)

api.upload_folder(
    folder_path=str(ORG_CARD_DIR),
    repo_id=REPO_ID,
    repo_type="space",
    allow_patterns=["README.md", "index.html"],
    commit_message="add org card",
)

print(f"Done — https://huggingface.co/tickertruthorg")

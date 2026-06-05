"""
Creates the tickertruthorg org card on HuggingFace.

HuggingFace org cards live in a model repo named after the org itself:
  tickertruthorg/tickertruthorg

Run from the repo root:
    HF_TOKEN=hf_... python3 releases/huggingface/org_card/upload_org_card.py
"""

import os
import sys
from pathlib import Path

from huggingface_hub import HfApi

REPO_ID = "tickertruthorg/tickertruthorg"
README = Path(__file__).parent / "README.md"

token = os.environ.get("HF_TOKEN", "").strip()
if not token:
    print("Error: HF_TOKEN not set.")
    print("Run: export HF_TOKEN=hf_your_token_here")
    sys.exit(1)

api = HfApi(token=token)

api.create_repo(
    repo_id=REPO_ID,
    repo_type="model",
    exist_ok=True,
    private=False,
)

api.upload_file(
    path_or_fileobj=README,
    path_in_repo="README.md",
    repo_id=REPO_ID,
    repo_type="model",
    commit_message="add org card",
)

print(f"Done — https://huggingface.co/tickertruthorg")

import os
from huggingface_hub import snapshot_download

# Replace with the correct repo name
repo_id = "openai/gpt-oss-20b"

snapshot_download(
    repo_id=repo_id,
    local_dir="./model",
    local_dir_use_symlinks=False,
    token=os.environ.get("HF_TOKEN")
)
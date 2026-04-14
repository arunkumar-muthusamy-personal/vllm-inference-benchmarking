import os
from huggingface_hub import snapshot_download

model_name = "Qwen2.5-32B-Instruct"
repo_id = f"Qwen/{model_name}"

snapshot_download(
    repo_id=repo_id,
    local_dir=f"./model",
    local_dir_use_symlinks=False,
    token=os.environ.get("HF_TOKEN")
)
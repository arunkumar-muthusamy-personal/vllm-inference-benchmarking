from huggingface_hub import snapshot_download

# Replace with the correct repo name
repo_id = "openai/gpt-oss-20b"

snapshot_download(
    repo_id=repo_id,
    local_dir="./models/gpt-oss-20b",
    local_dir_use_symlinks=False
    # token="YOUR_HF_TOKEN"  # optional if repo is public
)
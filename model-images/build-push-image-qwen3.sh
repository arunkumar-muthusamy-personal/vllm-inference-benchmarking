#!/bin/bash
set -e

VERSION="4.51.0"
MODEL_NAME="Qwen3-30B-A3B"
GH_USER_NAME="arunkumar-muthusamy-personal"
DOCKERFILE="Dockerfile.Qwen3-30B-A3B"
IMAGE_LATEST="ghcr.io/${GH_USER_NAME}/${MODEL_NAME}:latest"
IMAGE_VERSION="ghcr.io/${GH_USER_NAME}/${MODEL_NAME}:${VERSION}"

if [ -z "$GITHUB_PAT" ]; then
    echo "Error: GITHUB_PAT environment variable is not set. Exiting."
    exit 1
fi

# Step 1 — Build
echo "Building image..."
docker buildx create --use
docker buildx build --platform linux/amd64 \
    -f "$DOCKERFILE" \
    -t "$IMAGE_LATEST" \
    -t "$IMAGE_VERSION" \
    --load \
    .

echo "Build complete."

# Step 2 — Push
echo "Pushing image..."
echo "$GITHUB_PAT" | docker login ghcr.io -u "$GH_USER_NAME" --password-stdin

docker push "$IMAGE_LATEST"
docker push "$IMAGE_VERSION"

echo "Push complete."

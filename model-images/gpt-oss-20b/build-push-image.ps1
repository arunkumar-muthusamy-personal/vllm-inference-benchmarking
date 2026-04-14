$VERSION="4.55.0.dev0"
$MODEL_NAME="gpt-oss-20b-model"
$GH_USER_NAME="arunkumar-muthusamy-personal"
$DOCKERFILE="Dockerfile.gpt-oss-20b"

# Set GITHUB_PAT as an environment variable in your shell before running this script
# $env:GITHUB_PAT = "your_token_here"
if (-not $env:GITHUB_PAT) {
    Write-Error "GITHUB_PAT environment variable is not set. Exiting."
    exit 1
}

# Pipe it to Docker login
$env:GITHUB_PAT | docker login ghcr.io -u $GH_USER_NAME --password-stdin

docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 `
-f $DOCKERFILE `
-t "ghcr.io/${GH_USER_NAME}/${MODEL_NAME}:latest" `
-t "ghcr.io/${GH_USER_NAME}/${MODEL_NAME}:${VERSION}" `
--push `
.

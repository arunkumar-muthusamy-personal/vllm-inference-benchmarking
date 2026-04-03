#!/bin/bash
set -e

# Detect OS package manager
if command -v apt-get &>/dev/null; then
    PKG="apt-get"
    PKG_UPDATE="sudo apt-get update -y"
    PKG_INSTALL="sudo apt-get install -y"
elif command -v dnf &>/dev/null; then
    PKG="dnf"
    PKG_UPDATE="sudo dnf update -y"
    PKG_INSTALL="sudo dnf install -y"
elif command -v yum &>/dev/null; then
    PKG="yum"
    PKG_UPDATE="sudo yum update -y"
    PKG_INSTALL="sudo yum install -y"
else
    echo "Unsupported package manager. Exiting."
    exit 1
fi

echo "Detected package manager: $PKG"

echo "=============================="
echo "Updating system..."
echo "=============================="
$PKG_UPDATE

echo "=============================="
echo "Installing basic dependencies..."
echo "=============================="
if [[ "$PKG" == "apt-get" ]]; then
    $PKG_INSTALL curl wget git build-essential
else
    $PKG_INSTALL curl wget git gcc gcc-c++ make
fi

echo "=============================="
echo "Installing NVIDIA driver..."
echo "=============================="
if [[ "$PKG" == "apt-get" ]]; then
    $PKG_INSTALL nvidia-driver-535
else
    # Amazon Linux / RHEL — use DKMS driver from CUDA repo
    sudo dnf config-manager --add-repo https://developer.download.nvidia.com/compute/cuda/repos/amzn2023/x86_64/cuda-amzn2023.repo 2>/dev/null || \
    sudo dnf config-manager --add-repo https://developer.download.nvidia.com/compute/cuda/repos/rhel9/x86_64/cuda-rhel9.repo
    $PKG_INSTALL kernel-devel kernel-headers
    $PKG_INSTALL nvidia-driver nvidia-driver-cuda
fi

echo "Reboot required for NVIDIA driver. Re-run script after reboot."
read -p "Reboot now? (y/n): " REBOOT
if [[ "$REBOOT" == "y" ]]; then
    sudo reboot
    exit 0
fi

echo "=============================="
echo "Verifying NVIDIA driver..."
echo "=============================="
nvidia-smi || { echo "NVIDIA driver not working. Reboot may be needed."; exit 1; }

echo "=============================="
echo "Installing Docker..."
echo "=============================="
if [[ "$PKG" == "apt-get" ]]; then
    curl -fsSL https://get.docker.com | sh
else
    $PKG_INSTALL docker
    sudo systemctl enable docker
    sudo systemctl start docker
fi
sudo usermod -aG docker $USER

echo "=============================="
echo "Installing NVIDIA Container Toolkit..."
echo "=============================="
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list 2>/dev/null | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list 2>/dev/null || true

if [[ "$PKG" == "apt-get" ]]; then
    sudo apt-get update
    sudo apt-get install -y nvidia-container-toolkit
else
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo | \
        sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo
    $PKG_INSTALL nvidia-container-toolkit
fi

sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

echo "=============================="
echo "Testing GPU inside Docker..."
echo "=============================="
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi

echo "=============================="
echo "Setup complete."
echo "=============================="
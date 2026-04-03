#!/bin/bash

set -e

echo "=============================="
echo "Updating system..."
echo "=============================="
sudo apt update && sudo apt upgrade -y

echo "=============================="
echo "Installing basic dependencies..."
echo "=============================="
sudo apt install -y curl wget git build-essential

echo "=============================="
echo "Installing NVIDIA driver..."
echo "=============================="
sudo apt install -y nvidia-driver-535

echo "Reboot required for NVIDIA driver. Re-run script after reboot."
read -p "Reboot now? (y/n): " REBOOT
if [[ "$REBOOT" == "y" ]]; then
    sudo reboot
    exit 0
fi

echo "=============================="
echo "Verifying NVIDIA driver..."
echo "=============================="
nvidia-smi || { echo "NVIDIA driver not working"; exit 1; }

echo "=============================="
echo "Installing Docker..."
echo "=============================="
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

echo "=============================="
echo "Installing NVIDIA Container Toolkit..."
echo "=============================="
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)

curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | sudo apt-key add -

curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
sudo apt install -y nvidia-container-toolkit

sudo systemctl restart docker

echo "=============================="
echo "Testing GPU inside Docker..."
echo "=============================="
docker run --rm --gpus all nvidia/cuda:12.1.0-base nvidia-smi



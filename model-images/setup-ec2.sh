sudo dnf update -y && \
sudo dnf install -y git docker python3 python3-pip gcc make unzip tar wget && \
sudo systemctl start docker && \
sudo systemctl enable docker && \
sudo usermod -aG docker ec2-user && \
pip3 install --upgrade pip && \
pip3 install huggingface_hub hf_transfer
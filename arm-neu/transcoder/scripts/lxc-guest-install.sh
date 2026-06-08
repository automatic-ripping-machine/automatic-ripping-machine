#!/bin/bash
# ARM Transcoder - LXC Installation Script
# For Proxmox LXC containers with NVIDIA GPU passthrough
#
# Prerequisites:
#   - Privileged LXC container with GPU passthrough configured
#   - NVIDIA driver 580.119.02 installed (same as host)
#   - Shared storage mounts configured (NFS, SMB, etc.)
#
# Usage: Run this script inside the LXC container

set -e

echo "=== ARM Transcoder LXC Installation ==="

# Check if running as root
if [[ "$EUID" -ne 0 ]]; then
    echo "Please run as root"
    exit 1
fi

# Check NVIDIA driver
if ! command -v nvidia-smi &> /dev/null; then
    echo "ERROR: nvidia-smi not found. Install NVIDIA driver first:"
    echo "  wget https://us.download.nvidia.com/XFree86/Linux-x86_64/580.119.02/NVIDIA-Linux-x86_64-580.119.02.run"
    echo "  chmod +x NVIDIA-Linux-x86_64-580.119.02.run"
    echo "  ./NVIDIA-Linux-x86_64-580.119.02.run --no-kernel-module"
    exit 1
fi

echo "NVIDIA driver detected:"
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader

# Install dependencies
echo ""
echo "=== Installing dependencies ==="
apt-get update
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    handbrake-cli \
    mediainfo \
    curl \
    wget

# Create transcoder user
echo ""
echo "=== Creating transcoder user ==="
if ! id "transcoder" &>/dev/null; then
    useradd -m -s /bin/bash -G video transcoder
    echo "Created user 'transcoder'"
else
    echo "User 'transcoder' already exists"
fi

# Create directories
echo ""
echo "=== Creating directories ==="
mkdir -p /opt/arm-transcoder
mkdir -p /var/lib/arm-transcoder
mkdir -p /var/log/arm-transcoder

# Copy application files
echo ""
echo "=== Installing application ==="
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create virtual environment
python3 -m venv /opt/arm-transcoder/venv
source /opt/arm-transcoder/venv/bin/activate
pip install --upgrade pip
pip install -r "${SCRIPT_DIR}/requirements.txt"

# Copy source files
cp -r "${SCRIPT_DIR}/src/"* /opt/arm-transcoder/
cp -r "${SCRIPT_DIR}/presets" /opt/arm-transcoder/

# Create config file
if [[ ! -f /etc/arm-transcoder.env ]]; then
    cp "${SCRIPT_DIR}/.env.example" /etc/arm-transcoder.env
    echo "Created /etc/arm-transcoder.env - please edit this file"
fi

# Set ownership
chown -R transcoder:transcoder /opt/arm-transcoder
chown -R transcoder:transcoder /var/lib/arm-transcoder
chown -R transcoder:transcoder /var/log/arm-transcoder

# Install systemd service
echo ""
echo "=== Installing systemd service ==="
cat > /etc/systemd/system/arm-transcoder.service << 'EOF'
[Unit]
Description=ARM Transcoder - GPU Transcoding Service
After=network.target

[Service]
Type=simple
User=transcoder
Group=transcoder
WorkingDirectory=/opt/arm-transcoder
EnvironmentFile=/etc/arm-transcoder.env
ExecStart=/opt/arm-transcoder/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 5000
Restart=always
RestartSec=10

# Logging
StandardOutput=append:/var/log/arm-transcoder/service.log
StandardError=append:/var/log/arm-transcoder/service.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable arm-transcoder

echo ""
echo "=== Installation complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit /etc/arm-transcoder.env with your paths"
echo "  2. Ensure shared storage mounts are configured in /etc/fstab"
echo "  3. Start the service: systemctl start arm-transcoder"
echo "  4. Check status: systemctl status arm-transcoder"
echo "  5. View logs: tail -f /var/log/arm-transcoder/service.log"
echo ""
echo "Webhook URL: http://<this-container-ip>:5000/webhook/arm"

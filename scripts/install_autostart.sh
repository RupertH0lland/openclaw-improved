#!/bin/bash
# Install AI Orchestrator to start with system (systemd)
# Run: sudo ./install_autostart.sh
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
USER="${SUDO_USER:-$USER}"
PYTHON="$(which python3)"
SERVICE="ai-orchestrator.service"
cat > /tmp/$SERVICE << EOF
[Unit]
Description=AI Orchestrator
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$ROOT
ExecStart=$PYTHON $ROOT/main.py run
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo mv /tmp/$SERVICE /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE
echo "Installed. Start with: sudo systemctl start ai-orchestrator"

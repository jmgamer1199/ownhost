#!/usr/bin/env bash
# Installs the agent as a service on a Linux computer (e.g. the homelab), from source with Python.
# Usage:  sudo bash scripts/install-agent-linux.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Run this script with sudo." >&2
    exit 1
fi

SRC="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR=/opt/ownhost
DATA_DIR=/var/lib/ownhost
USER_NAME=ownhost

if ! command -v python3 >/dev/null; then
    echo "Install Python 3.11+ first (sudo apt install python3 python3-venv)." >&2
    exit 1
fi

id "$USER_NAME" &>/dev/null || useradd --system --home "$DATA_DIR" --shell /usr/sbin/nologin "$USER_NAME"
mkdir -p "$APP_DIR" "$DATA_DIR"
cp -r "$SRC/ownhost" "$SRC/pyproject.toml" "$APP_DIR/"
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install "$APP_DIR"
chown -R "$USER_NAME:$USER_NAME" "$DATA_DIR"

cp "$SRC/scripts/ownhost-agent.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now ownhost-agent

sleep 2
echo
echo "Agent installed and running."
echo "This computer's IP: $(hostname -I | awk '{print $1}')   Port: 8765"
if command -v tailscale >/dev/null && TS_IP=$(tailscale ip -4 2>/dev/null); then
    echo "Tailscale IP:        $TS_IP   (to connect from outside your home)"
fi
echo "Token: $(sudo -u "$USER_NAME" OWNHOST_DATA_DIR="$DATA_DIR" "$APP_DIR/venv/bin/python" -m ownhost.agent --show-token)"
echo
echo "Add it in the app with 'Connect to a computer'. If you use ufw:"
echo "  sudo ufw allow 8765/tcp && sudo ufw allow 25565/tcp && sudo ufw allow 5520/udp"
echo "  sudo ufw allow 19132/udp   # only if you use crossplay (Geyser)"

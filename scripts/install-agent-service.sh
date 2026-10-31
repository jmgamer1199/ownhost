#!/usr/bin/env bash
# Turns this Linux computer into a server: installs the Ownhost agent as a service that starts
# automatically when the computer boots, even if nobody logs in. It is managed from the app on another PC.
#
# Usage (in the folder that contains the Ownhost binary):
#     sudo bash install-agent-service.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Run this script with sudo:  sudo bash $0" >&2
    exit 1
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
APP_DIR=/opt/ownhost
DATA_DIR=/var/lib/ownhost
USER_NAME=ownhost
PORT=8765

if [[ ! -f "$HERE/Ownhost" ]]; then
    echo "Can't find the Ownhost file next to this script." >&2
    exit 1
fi

NOLOGIN=$(command -v nologin || echo /usr/sbin/nologin)
id "$USER_NAME" &>/dev/null || useradd --system --home "$DATA_DIR" --shell "$NOLOGIN" "$USER_NAME"
mkdir -p "$APP_DIR" "$DATA_DIR"
systemctl stop ownhost-agent 2>/dev/null || true
install -m 755 "$HERE/Ownhost" "$APP_DIR/Ownhost"
chown -R "$USER_NAME:$USER_NAME" "$DATA_DIR"

cat > /etc/systemd/system/ownhost-agent.service <<EOF
[Unit]
Description=Ownhost - agent
After=network-online.target
Wants=network-online.target

[Service]
User=$USER_NAME
Environment=OWNHOST_DATA_DIR=$DATA_DIR
ExecStart=$APP_DIR/Ownhost --agent --bind 0.0.0.0 --port $PORT
# Only the agent receives the stop signal: it stops each server with "stop" so the world gets saved.
KillMode=mixed
TimeoutStopSec=120
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now ownhost-agent

# Firewall (only if ufw or firewalld is active): agent, Minecraft Java, Bedrock/Geyser and Hytale.
if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
    ufw allow $PORT/tcp >/dev/null      # the app connects to the agent
    ufw allow $PORT/udp >/dev/null      # the app finds the computer on the network
    ufw allow 25565:25575/tcp >/dev/null  # Minecraft Java
    ufw allow 19132:19140/udp >/dev/null  # Bedrock / Geyser
    ufw allow 19132:19140/tcp >/dev/null  # Geyser (NetherNet)
    ufw allow 5520:5530/udp >/dev/null    # Hytale
    echo "Firewall (ufw): ports opened."
elif command -v firewall-cmd >/dev/null && systemctl is-active --quiet firewalld; then
    firewall-cmd --permanent --add-port=$PORT/tcp --add-port=$PORT/udp --add-port=25565-25575/tcp \
        --add-port=19132-19140/udp --add-port=19132-19140/tcp --add-port=5520-5530/udp >/dev/null
    firewall-cmd --reload >/dev/null
    echo "Firewall (firewalld): ports opened."
fi

for _ in $(seq 1 15); do
    [[ -f "$DATA_DIR/agent.json" ]] && break
    sleep 1
done
TOKEN=$(runuser -u "$USER_NAME" -- env OWNHOST_DATA_DIR="$DATA_DIR" "$APP_DIR/Ownhost" --agent --show-token 2>/dev/null | tail -1)
# "hostname -I" doesn't exist on every distribution (e.g. Arch): use "ip" if available.
LAN_IP=$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<NF;i++) if ($i=="src") print $(i+1)}' | head -1)
[[ -z "$LAN_IP" ]] && LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}')

echo
echo "Done: the agent is running and will start automatically with the computer."
echo "  Network IP:    ${LAN_IP:-unknown}   Port: $PORT"
if command -v tailscale >/dev/null && TS_IP=$(tailscale ip -4 2>/dev/null); then
    echo "  Tailscale IP:  $TS_IP   (to manage it from outside your home)"
fi
echo "  Token:         $TOKEN"
echo
echo "In the app on the other PC: \"Connect to a computer\", pick this computer under \"Found on your network\" and paste the token."
echo "To see what it's doing:  journalctl -u ownhost-agent -f"

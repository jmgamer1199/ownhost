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
chmod 750 "$DATA_DIR"   # agent.json holds the token: other users of this computer can't read it

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
# Hardening that doesn't get in the way of Java or Bedrock: the service can't gain privileges.
NoNewPrivileges=yes
LockPersonality=yes
RestrictSUIDSGID=yes

[Install]
WantedBy=multi-user.target
EOF

# Updates from the app: the agent (which can't change its own program: it belongs to root) creates an empty file;
# this unit sees it and runs the updater as root. The updater takes nothing from the agent: it asks GitHub for the
# latest version, only accepts a newer one and checks its SHA-256 before replacing the binary.
cat > /etc/systemd/system/ownhost-update.path <<EOF
[Unit]
Description=Ownhost - update asked for by the agent

[Path]
PathExists=$DATA_DIR/update-requested
Unit=ownhost-update.service

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/ownhost-update.service <<EOF
[Unit]
Description=Ownhost - update the agent to the latest published version
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=600
StartLimitBurst=3

[Service]
Type=oneshot
Environment=OWNHOST_DATA_DIR=$DATA_DIR
ExecStart=$APP_DIR/Ownhost --apply-update
TimeoutStartSec=900
NoNewPrivileges=yes
PrivateTmp=yes
ProtectHome=yes
ProtectSystem=strict
ReadWritePaths=$APP_DIR $DATA_DIR
ProtectKernelTunables=yes
ProtectControlGroups=yes
LockPersonality=yes
RestrictSUIDSGID=yes
EOF

systemctl daemon-reload
systemctl enable --now ownhost-agent
systemctl enable --now ownhost-update.path

# Firewall (only if ufw or firewalld is active), ONLY for the home network and Tailscale: from the internet the
# ports stay closed even if a router forwarded them. Same rules as the app (ownhost/app/firewall.py).
SOURCES="192.168.0.0/16 10.0.0.0/8 172.16.0.0/12 100.64.0.0/10 fc00::/7 fe80::/10"
# agent (app / discovery), Minecraft Java, Bedrock/Geyser, Hytale, web map, Bedrock NetherNet, Bedrock LAN
PORTS="$PORT/tcp $PORT/udp 25565:25575/tcp 19132:19140/udp 19132:19140/tcp 5520:5530/udp 8100:8110/tcp 19200:19299/udp 7551/udp"
if command -v ufw >/dev/null && [[ "$(ufw status)" == *"Status: active"* ]]; then
    for rule in $PORT $PORTS 25565/tcp 19132/udp 5520/udp; do   # rules of older versions, open to anyone
        ufw delete allow "$rule" >/dev/null 2>&1 || true
    done
    for source in $SOURCES; do
        for p in $PORTS; do
            ufw allow from "$source" to any port "${p%/*}" proto "${p#*/}" comment Ownhost >/dev/null
        done
    done
    echo "Firewall (ufw): ports opened for the home network and Tailscale only."
elif command -v firewall-cmd >/dev/null && systemctl is-active --quiet firewalld; then
    for p in $PORTS; do
        port="${p%/*}"; port="${port/:/-}"; proto="${p#*/}"
        firewall-cmd --permanent --remove-port="$port/$proto" >/dev/null 2>&1 || true   # older versions
        for source in $SOURCES; do
            family=ipv4; [[ $source == *:* ]] && family=ipv6
            firewall-cmd --permanent --add-rich-rule="rule family=\"$family\" source address=\"$source\" port port=\"$port\" protocol=\"$proto\" accept" >/dev/null
        done
    done
    firewall-cmd --reload >/dev/null
    echo "Firewall (firewalld): ports opened for the home network and Tailscale only."
fi

for _ in $(seq 1 15); do
    [[ -f "$DATA_DIR/agent.json" ]] && break
    sleep 1
done
TOKEN=$(runuser -u "$USER_NAME" -- env OWNHOST_DATA_DIR="$DATA_DIR" "$APP_DIR/Ownhost" --agent --show-token 2>/dev/null | tail -1 || true)
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
echo "Updates: from the app (the update button on this computer's page), or by hand:  sudo touch $DATA_DIR/update-requested  (log: journalctl -u ownhost-update)"

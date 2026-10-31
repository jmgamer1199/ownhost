#!/usr/bin/env bash
# Instala el agente como servicio en un equipo Linux (p. ej. el homelab).
# Uso:  sudo bash scripts/instalar-agente-linux.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Ejecuta este script con sudo." >&2
    exit 1
fi

SRC="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR=/opt/ownhost
DATA_DIR=/var/lib/ownhost
USER_NAME=ownhost

if ! command -v python3 >/dev/null; then
    echo "Instala Python 3.11+ primero (sudo apt install python3 python3-venv)." >&2
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
echo "Agente instalado y en marcha."
echo "IP de este equipo: $(hostname -I | awk '{print $1}')   Puerto: 8765"
if command -v tailscale >/dev/null && TS_IP=$(tailscale ip -4 2>/dev/null); then
    echo "IP de Tailscale:   $TS_IP   (para conectar desde fuera de casa)"
fi
echo "Token: $(sudo -u "$USER_NAME" OWNHOST_DATA_DIR="$DATA_DIR" "$APP_DIR/venv/bin/python" -m ownhost.agent --show-token)"
echo
echo "Añádelo en la app con 'Añadir equipo'. Si usas ufw:"
echo "  sudo ufw allow 8765/tcp && sudo ufw allow 25565/tcp && sudo ufw allow 5520/udp"
echo "  sudo ufw allow 19132/udp   # solo si usas multiplataforma (Geyser)"

#!/usr/bin/env bash
# Convierte este equipo Linux en servidor: instala el agente de Ownhost como servicio, que arranca
# solo al encender el equipo aunque nadie inicie sesión. Se gestiona desde la app de otro PC.
#
# Uso (en la carpeta donde está el binario Ownhost):
#     sudo bash instalar-agente-servicio.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Ejecuta este script con sudo:  sudo bash $0" >&2
    exit 1
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
APP_DIR=/opt/ownhost
DATA_DIR=/var/lib/ownhost
USER_NAME=ownhost
PORT=8765

if [[ ! -f "$HERE/Ownhost" ]]; then
    echo "No encuentro el archivo Ownhost junto a este script." >&2
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
Description=Ownhost - agente
After=network-online.target
Wants=network-online.target

[Service]
User=$USER_NAME
Environment=OWNHOST_DATA_DIR=$DATA_DIR
ExecStart=$APP_DIR/Ownhost --agent --bind 0.0.0.0 --port $PORT
# Solo el agente recibe la orden de parar: él apaga cada servidor con "stop" para que guarde el mundo.
KillMode=mixed
TimeoutStopSec=120
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now ownhost-agent

# Cortafuegos (solo si ufw está activo): agente, Minecraft Java, Bedrock/Geyser y Hytale.
if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
    ufw allow $PORT/tcp >/dev/null      # la app se conecta al agente
    ufw allow $PORT/udp >/dev/null      # la app encuentra el equipo en la red
    ufw allow 25565:25575/tcp >/dev/null  # Minecraft Java
    ufw allow 19132:19140/udp >/dev/null  # Bedrock / Geyser
    ufw allow 19132:19140/tcp >/dev/null  # Geyser (NetherNet)
    ufw allow 5520:5530/udp >/dev/null    # Hytale
    echo "Cortafuegos (ufw): puertos abiertos."
elif command -v firewall-cmd >/dev/null && systemctl is-active --quiet firewalld; then
    firewall-cmd --permanent --add-port=$PORT/tcp --add-port=$PORT/udp --add-port=25565-25575/tcp \
        --add-port=19132-19140/udp --add-port=19132-19140/tcp --add-port=5520-5530/udp >/dev/null
    firewall-cmd --reload >/dev/null
    echo "Cortafuegos (firewalld): puertos abiertos."
fi

for _ in $(seq 1 15); do
    [[ -f "$DATA_DIR/agent.json" ]] && break
    sleep 1
done
TOKEN=$(runuser -u "$USER_NAME" -- env OWNHOST_DATA_DIR="$DATA_DIR" "$APP_DIR/Ownhost" --agent --show-token 2>/dev/null | tail -1)
# "hostname -I" no existe en todas las distribuciones (p. ej. Arch): se usa "ip" si está.
LAN_IP=$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<NF;i++) if ($i=="src") print $(i+1)}' | head -1)
[[ -z "$LAN_IP" ]] && LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}')

echo
echo "Listo: el agente está en marcha y arrancará solo con el equipo."
echo "  IP en tu red:  ${LAN_IP:-desconocida}   Puerto: $PORT"
if command -v tailscale >/dev/null && TS_IP=$(tailscale ip -4 2>/dev/null); then
    echo "  IP Tailscale:  $TS_IP   (para gestionarlo desde fuera de casa)"
fi
echo "  Token:         $TOKEN"
echo
echo "En la app del otro PC: «Conectar a un equipo», elige este equipo en «Detectados» y pega el token."
echo "Para ver lo que hace:  journalctl -u ownhost-agent -f"

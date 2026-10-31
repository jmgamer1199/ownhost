#!/usr/bin/env bash
# Genera en dist/linux/:
#   Ownhost-x86_64.AppImage  -> para escritorio (doble clic)
#   Ownhost                  -> binario simple, p. ej. para el agente en un servidor sin escritorio
#
# Se ejecuta dentro de un contenedor AlmaLinux 8 (lo lanza crear-exe.ps1): compilar sobre una glibc
# antigua (2.28, de 2018) hace que el binario funcione en prácticamente cualquier distribución de
# escritorio actual: Debian 10+, Ubuntu 20.04+, RHEL/Rocky/Alma 8+, Fedora, Arch/CachyOS, openSUSE...
# (no en las que usan musl en vez de glibc, como Alpine).
#
# Uso dentro del contenedor:  bash scripts/crear-binario-linux.sh /src /src/dist/linux
set -euo pipefail

SRC="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
OUT="${2:-$SRC/dist/linux}"
WORK=/tmp/ownhost-build

if command -v dnf >/dev/null && [[ $EUID -eq 0 ]]; then
    # AlmaLinux 8: Python 3.12 viene en sus repositorios; las bibliotecas de Qt, de EPEL y del sistema.
    dnf -y -q install epel-release >/dev/null
    dnf -y -q install python3.12 python3.12-devel binutils file findutils libatomic \
        mesa-libGL mesa-libEGL libxkbcommon libxkbcommon-x11 fontconfig dbus-libs glib2 \
        xcb-util-cursor xcb-util-wm xcb-util-image xcb-util-keysyms xcb-util-renderutil libxcb >/dev/null
elif command -v apt-get >/dev/null && [[ $EUID -eq 0 ]]; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    if ! command -v python3.12 >/dev/null; then
        # Ubuntu 22.04 trae Python 3.10: el 3.12 viene del PPA deadsnakes.
        apt-get install -y -qq --no-install-recommends software-properties-common gpg-agent >/dev/null
        add-apt-repository -y ppa:deadsnakes/ppa >/dev/null
        apt-get update -qq
        apt-get install -y -qq --no-install-recommends python3.12 python3.12-venv python3.12-dev >/dev/null
    fi
    # Bibliotecas que necesita Qt para dibujar ventanas; PyInstaller las incluye en el binario.
    apt-get install -y -qq --no-install-recommends binutils curl ca-certificates file libgl1 libegl1 libxkbcommon0 \
        libxkbcommon-x11-0 libfontconfig1 libdbus-1-3 libglib2.0-0 libxcb-cursor0 libxcb-icccm4 \
        libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
        libxcb-xinerama0 libxcb-xkb1 >/dev/null
fi
PYTHON=$(command -v python3.12 || command -v python3)

# Se compila sobre una copia para no dejar archivos temporales en la carpeta del proyecto.
rm -rf "$WORK"
mkdir -p "$WORK/src"
cp -r "$SRC/ownhost" "$SRC/pyproject.toml" "$SRC/scripts" "$WORK/src/"
[[ -f "$SRC/curseforge.key" ]] && cp "$SRC/curseforge.key" "$WORK/src/"

"$PYTHON" -m venv "$WORK/venv"
"$WORK/venv/bin/pip" install -q --upgrade pip
"$WORK/venv/bin/pip" install -q "$WORK/src[app]" pyinstaller

"$WORK/venv/bin/python" "$WORK/src/scripts/embed_key.py"
HIDDEN=(--hidden-import ownhost._build)
[[ -f "$WORK/src/ownhost/_embedded.py" ]] && HIDDEN+=(--hidden-import ownhost._embedded)

COMMON=(--noconfirm --clean --windowed --name Ownhost
    --add-data "$WORK/src/ownhost/app/assets:ownhost/app/assets"
    --add-data "$WORK/src/ownhost/agent/web:ownhost/agent/web"
    --paths "$WORK/src" --collect-submodules uvicorn --collect-submodules websockets --collect-submodules ownhost.locale "${HIDDEN[@]}"
    --specpath "$WORK")

# 1) Binario de un solo archivo: útil para servidores sin escritorio (Ownhost --agent).
"$WORK/venv/bin/pyinstaller" "${COMMON[@]}" --onefile \
    --distpath "$OUT" --workpath "$WORK/build-onefile" "$WORK/src/ownhost/app/__main__.py"

# 2) AppImage para escritorio: versión en carpeta (arranca más rápido) empaquetada con appimagetool.
"$WORK/venv/bin/pyinstaller" "${COMMON[@]}" --onedir \
    --distpath "$WORK/onedir" --workpath "$WORK/build-onedir" "$WORK/src/ownhost/app/__main__.py"

APPDIR="$WORK/Ownhost.AppDir"
mkdir -p "$APPDIR/usr/lib"
cp -r "$WORK/onedir/Ownhost" "$APPDIR/usr/lib/"
cp "$WORK/src/ownhost/app/assets/icon.png" "$APPDIR/ownhost.png"
cp "$WORK/src/ownhost/app/assets/icon.png" "$APPDIR/.DirIcon"
cat > "$APPDIR/ownhost.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Ownhost
Comment=Servidores de Minecraft y Hytale en tu red
Exec=Ownhost
Icon=ownhost
Terminal=false
Categories=Game;Utility;
EOF
cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/lib/Ownhost/Ownhost" "$@"
EOF
chmod +x "$APPDIR/AppRun"

APPIMAGETOOL_VERSION=1.9.1
TOOL="$WORK/appimagetool"
curl -fsSL -o "$TOOL.AppImage" \
    "https://github.com/AppImage/appimagetool/releases/download/$APPIMAGETOOL_VERSION/appimagetool-x86_64.AppImage"
chmod +x "$TOOL.AppImage"
# En Docker no hay FUSE: se extrae la herramienta y se ejecuta directamente.
(cd "$WORK" && "$TOOL.AppImage" --appimage-extract >/dev/null)
ARCH=x86_64 "$WORK/squashfs-root/AppRun" --no-appstream "$APPDIR" "$OUT/Ownhost-x86_64.AppImage"

cp "$SRC/scripts/instalar-app-linux.sh" "$SRC/scripts/instalar-agente-servicio.sh" "$OUT/"
cp "$WORK/src/ownhost/app/assets/icon.png" "$OUT/ownhost.png"
chmod +x "$OUT/Ownhost" "$OUT/Ownhost-x86_64.AppImage" "$OUT/instalar-app-linux.sh" \
    "$OUT/instalar-agente-servicio.sh"
rm -rf "$WORK"
echo "Listo: $OUT/Ownhost-x86_64.AppImage"
echo "Listo: $OUT/Ownhost"

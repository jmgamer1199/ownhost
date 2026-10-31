#!/usr/bin/env bash
# Instala el AppImage de Ownhost para el usuario actual y lo añade al menú de aplicaciones.
# Uso: bash instalar-app-linux.sh   (en la carpeta donde está Ownhost-x86_64.AppImage)
#
# Funciona en cualquier distribución con glibc 2.28 o más reciente (Debian, Ubuntu, Mint, Fedora,
# RHEL/Rocky/Alma, Arch/Manjaro/CachyOS, openSUSE...). Si faltan las pocas bibliotecas gráficas del
# sistema que la ventana necesita (OpenGL/EGL, fontconfig), las instala con el administrador de paquetes.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/Applications"
APPS="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons/hicolor/256x256/apps"

# --- Bibliotecas del sistema que no van dentro del AppImage -------------------------------------
falta_lib() {
    # ldconfig puede estar en /sbin y no en el PATH de un usuario normal. La lista se guarda antes
    # de buscar: con pipefail, "ldconfig | grep -q" falla por SIGPIPE aunque la biblioteca esté.
    local ldc
    ldc=$(command -v ldconfig || echo /sbin/ldconfig)
    [[ -z "${LIBS_SISTEMA:-}" ]] && LIBS_SISTEMA=$("$ldc" -p 2>/dev/null || true)
    ! grep -q "$1" <<<"$LIBS_SISTEMA"
}

FALTAN=()
for lib in libGL.so.1 libEGL.so.1 libfontconfig.so.1; do
    falta_lib "$lib" && FALTAN+=("$lib")
done

if (( ${#FALTAN[@]} )); then
    echo "Faltan bibliotecas gráficas: ${FALTAN[*]}"
    SUDO=""
    [[ $EUID -ne 0 ]] && SUDO="sudo"
    if command -v apt-get >/dev/null; then
        CMD="$SUDO apt-get install -y libgl1 libegl1 libfontconfig1 fonts-dejavu-core"
    elif command -v dnf >/dev/null; then
        CMD="$SUDO dnf install -y mesa-libGL mesa-libEGL fontconfig dejavu-sans-fonts"
    elif command -v yum >/dev/null; then
        CMD="$SUDO yum install -y mesa-libGL mesa-libEGL fontconfig dejavu-sans-fonts"
    elif command -v pacman >/dev/null; then
        CMD="$SUDO pacman -S --needed --noconfirm mesa fontconfig ttf-dejavu"
    elif command -v zypper >/dev/null; then
        CMD="$SUDO zypper -n install Mesa-libGL1 Mesa-libEGL1 fontconfig dejavu-fonts"
    elif command -v xbps-install >/dev/null; then
        CMD="$SUDO xbps-install -y mesa fontconfig dejavu-fonts-ttf"
    elif command -v emerge >/dev/null; then
        CMD="$SUDO emerge --noreplace media-libs/mesa media-libs/fontconfig media-fonts/dejavu"
    else
        CMD=""
    fi
    if [[ -n "$CMD" ]]; then
        echo "Instalándolas con: $CMD"
        if command -v apt-get >/dev/null; then
            $SUDO apt-get update -qq || true
        fi
        $CMD || echo "No se pudieron instalar. Instálalas a mano con: $CMD" >&2
    else
        echo "Instálalas con el administrador de paquetes de tu distribución (paquetes de Mesa OpenGL/EGL y fontconfig)." >&2
    fi
fi

# --- AppImage + acceso en el menú ---------------------------------------------------------------
mkdir -p "$DEST" "$APPS" "$ICONS"
install -m 755 "$HERE/Ownhost-x86_64.AppImage" "$DEST/Ownhost.AppImage"
install -m 644 "$HERE/ownhost.png" "$ICONS/ownhost.png"

# Sin FUSE (contenedores, algunas instalaciones mínimas) el AppImage no puede montarse: se le pide
# que se extraiga a sí mismo al arrancar, que funciona en cualquier sistema.
EXEC="$DEST/Ownhost.AppImage"
if [[ ! -e /dev/fuse ]] || { ! command -v fusermount >/dev/null && ! command -v fusermount3 >/dev/null; }; then
    EXEC="env APPIMAGE_EXTRACT_AND_RUN=1 $EXEC"
fi

cat > "$APPS/ownhost.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Ownhost
Comment=Servidores de Minecraft y Hytale en tu red
Exec=$EXEC
Icon=ownhost
Terminal=false
Categories=Game;Utility;
EOF
command -v update-desktop-database >/dev/null && update-desktop-database "$APPS" 2>/dev/null || true

echo "Instalado. Búscalo como «Ownhost» en el menú, o ejecuta: $EXEC"

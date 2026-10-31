#!/usr/bin/env bash
# Installs the Ownhost AppImage for the current user and adds it to the applications menu.
# Usage: bash install-app-linux.sh   (in the folder that contains Ownhost-x86_64.AppImage)
#
# Works on any distribution with glibc 2.28 or newer (Debian, Ubuntu, Mint, Fedora,
# RHEL/Rocky/Alma, Arch/Manjaro/CachyOS, openSUSE...). If the few system graphics libraries the
# window needs (OpenGL/EGL, fontconfig) are missing, it installs them with the package manager.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/Applications"
APPS="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons/hicolor/256x256/apps"

# --- System libraries that are not bundled in the AppImage ---------------------------------------
lib_missing() {
    # ldconfig may be in /sbin and not in a regular user's PATH. The list is saved before
    # searching: with pipefail, "ldconfig | grep -q" fails due to SIGPIPE even if the library is there.
    local ldc
    ldc=$(command -v ldconfig || echo /sbin/ldconfig)
    [[ -z "${SYSTEM_LIBS:-}" ]] && SYSTEM_LIBS=$("$ldc" -p 2>/dev/null || true)
    ! grep -q "$1" <<<"$SYSTEM_LIBS"
}

MISSING=()
for lib in libGL.so.1 libEGL.so.1 libfontconfig.so.1; do
    lib_missing "$lib" && MISSING+=("$lib")
done

if (( ${#MISSING[@]} )); then
    echo "Missing graphics libraries: ${MISSING[*]}"
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
        echo "Installing them with: $CMD"
        if command -v apt-get >/dev/null; then
            $SUDO apt-get update -qq || true
        fi
        $CMD || echo "They could not be installed. Install them by hand with: $CMD" >&2
    else
        echo "Install them with your distribution's package manager (Mesa OpenGL/EGL and fontconfig packages)." >&2
    fi
fi

# --- AppImage + menu entry ----------------------------------------------------------------------
mkdir -p "$DEST" "$APPS" "$ICONS"
install -m 755 "$HERE/Ownhost-x86_64.AppImage" "$DEST/Ownhost.AppImage"
install -m 644 "$HERE/ownhost.png" "$ICONS/ownhost.png"

# Without FUSE (containers, some minimal installs) the AppImage can't be mounted: ask it to
# extract itself on startup, which works on any system.
EXEC="$DEST/Ownhost.AppImage"
if [[ ! -e /dev/fuse ]] || { ! command -v fusermount >/dev/null && ! command -v fusermount3 >/dev/null; }; then
    EXEC="env APPIMAGE_EXTRACT_AND_RUN=1 $EXEC"
fi

cat > "$APPS/ownhost.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Ownhost
Comment=Minecraft and Hytale servers on your network
Exec=$EXEC
Icon=ownhost
Terminal=false
Categories=Game;Utility;
EOF
command -v update-desktop-database >/dev/null && update-desktop-database "$APPS" 2>/dev/null || true

echo "Installed. Look for \"Ownhost\" in the menu, or run: $EXEC"

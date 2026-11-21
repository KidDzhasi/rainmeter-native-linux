#!/usr/bin/env bash
# =============================================================================
# Trad Desktop — Flatpak Bundle Builder
# Builds and exports dist/trad-desktop.flatpak using built-in 'flatpak'
# commands (no flatpak-builder package required!).
#
# Usage:
#   ./scripts/build-flatpak.sh
#   flatpak install --user -y dist/trad-desktop.flatpak
#   flatpak run com.github.kiddzhasi.TradDesktop
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

APP_ID="com.github.kiddzhasi.TradDesktop"
STAGE_DIR="${ROOT_DIR}/dist/flatpak-stage"
REPO_DIR="${ROOT_DIR}/dist/flatpak-repo"
OUT_DIR="${ROOT_DIR}/dist"
BUNDLE_FILE="${OUT_DIR}/trad-desktop.flatpak"

echo "================================================================"
echo "  Building Flatpak Bundle: ${BUNDLE_FILE}"
echo "================================================================"

if ! command -v flatpak >/dev/null 2>&1; then
  echo "Error: 'flatpak' is not installed."
  exit 1
fi

RUNTIME_VER=""
for ver in 51 50 49 48 47 46; do
  if [ -d "/var/lib/flatpak/runtime/org.gnome.Platform/x86_64/${ver}" ] || \
     [ -d "${HOME}/.local/share/flatpak/runtime/org.gnome.Platform/x86_64/${ver}" ]; then
    RUNTIME_VER="$ver"
    break
  fi
done

if [ -z "$RUNTIME_VER" ]; then
  echo "[1/4] Installing org.gnome.Platform from Flathub..."
  RUNTIME_VER="47"
  flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
  flatpak install --user -y flathub "org.gnome.Platform//${RUNTIME_VER}"
else
  echo "[1/4] Using installed runtime: org.gnome.Platform//${RUNTIME_VER}"
fi

echo "[2/4] Compiling C++ engine..."
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"

echo "[3/4] Staging Flatpak application files..."
rm -rf "$STAGE_DIR" "$REPO_DIR"
flatpak build-init "$STAGE_DIR" "$APP_ID" org.gnome.Platform org.gnome.Platform "$RUNTIME_VER"

APP_FILES="${STAGE_DIR}/files"
mkdir -p "${APP_FILES}/bin" \
         "${APP_FILES}/lib" \
         "${APP_FILES}/share/trad-desktop" \
         "${APP_FILES}/share/applications" \
         "${APP_FILES}/share/metainfo" \
         "${APP_FILES}/share/icons/hicolor/512x512/apps"

install -m755 build/rainmeter-native "${APP_FILES}/bin/rainmeter-native"
install -m755 build/rmskin-unpacker "${APP_FILES}/bin/rmskin-unpacker"
install -m755 launcher_gui.py "${APP_FILES}/share/trad-desktop/launcher_gui.py"
cp -r assets suites widgets community gnome-extension "${APP_FILES}/share/trad-desktop/"

cat > "${APP_FILES}/bin/trad-desktop-gui" <<'EOF'
#!/usr/bin/env sh
export LD_LIBRARY_PATH="/app/lib:${LD_LIBRARY_PATH:-}"
exec python3 /app/share/trad-desktop/launcher_gui.py "$@"
EOF
chmod 755 "${APP_FILES}/bin/trad-desktop-gui"

install -m644 flatpak/com.github.kiddzhasi.TradDesktop.desktop \
  "${APP_FILES}/share/applications/${APP_ID}.desktop"
install -m644 flatpak/com.github.kiddzhasi.TradDesktop.metainfo.xml \
  "${APP_FILES}/share/metainfo/${APP_ID}.metainfo.xml"
install -m644 assets/trad-engine.png \
  "${APP_FILES}/share/icons/hicolor/512x512/apps/${APP_ID}.png"

RUNTIME_LIB_SYS="/var/lib/flatpak/runtime/org.gnome.Platform/x86_64/${RUNTIME_VER}/active/files/lib/x86_64-linux-gnu"
RUNTIME_LIB_USR="${HOME}/.local/share/flatpak/runtime/org.gnome.Platform/x86_64/${RUNTIME_VER}/active/files/lib/x86_64-linux-gnu"

for so in $(ldd build/rainmeter-native build/rmskin-unpacker | awk '/=> \// {print $3}' | sort -u); do
  base="$(basename "$so")"
  if [ ! -e "${RUNTIME_LIB_SYS}/${base}" ] && [ ! -e "${RUNTIME_LIB_USR}/${base}" ]; then
    cp -L "$so" "${APP_FILES}/lib/${base}"
  fi
done

flatpak build-finish "$STAGE_DIR" \
  --command=trad-desktop-gui \
  --share=ipc \
  --share=network \
  --socket=wayland \
  --socket=x11 \
  --socket=pulseaudio \
  --device=dri \
  --env=LD_LIBRARY_PATH=/app/lib \
  --talk-name=org.freedesktop.DBus \
  --talk-name='org.mpris.MediaPlayer2.*' \
  --filesystem=xdg-config/rainmeter-native:create \
  --filesystem=xdg-cache/trad-desktop:create \
  --filesystem=xdg-download:ro

echo "[4/4] Exporting single-file Flatpak bundle to ${BUNDLE_FILE}..."
mkdir -p "$OUT_DIR"

cat > "${STAGE_DIR}/validate-icon.sh" <<'EOF'
#!/usr/bin/env sh
for last_arg in "$@"; do :; done
if /usr/libexec/flatpak-validate-icon 512 512 "$last_arg" 2>/dev/null; then
  exit 0
fi
printf '[Icon Validator]\nformat=png\nwidth=512\n'
EOF
chmod 755 "${STAGE_DIR}/validate-icon.sh"

FLATPAK_VALIDATE_ICON="${STAGE_DIR}/validate-icon.sh" flatpak build-export "$REPO_DIR" "$STAGE_DIR"
rm -f "${STAGE_DIR}/validate-icon.sh"
flatpak build-bundle "$REPO_DIR" "$BUNDLE_FILE" "$APP_ID"
rm -rf "$STAGE_DIR" "$REPO_DIR"

echo "================================================================"
echo "✅ Flatpak bundle created: ${BUNDLE_FILE}"
echo "   Install with: flatpak install --user -y ${BUNDLE_FILE}"
echo "   Run with:     flatpak run ${APP_ID}"
echo "================================================================"

#!/usr/bin/env bash
# =============================================================================
# Trad Rainmeter — Flatpak Bundle Builder
# Builds and exports dist/trad-rainmeter.flatpak using built-in 'flatpak'
# commands (no flatpak-builder package required!).
#
# Usage:
#   ./scripts/build-flatpak.sh
#   flatpak install --user -y dist/trad-rainmeter.flatpak
#   flatpak run com.github.kiddzhasi.TradRainmeter
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

APP_ID="com.github.kiddzhasi.TradRainmeter"
STAGE_DIR="${ROOT_DIR}/dist/flatpak-stage"
REPO_DIR="${ROOT_DIR}/dist/flatpak-repo"
OUT_DIR="${ROOT_DIR}/dist"
BUNDLE_FILE="${OUT_DIR}/trad-rainmeter.flatpak"

echo "================================================================"
echo "  Building Flatpak Bundle: ${BUNDLE_FILE}"
echo "================================================================"

if ! command -v flatpak >/dev/null 2>&1; then
  echo "Error: 'flatpak' is not installed."
  exit 1
fi

# 1. Detect installed org.gnome.Platform runtime version (51, 50, 48, 47, 46)
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

# 2. Ensure C++ binaries are compiled
echo "[2/4] Compiling C++ engine..."
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"

# 3. Initialize Flatpak build directory and populate /app
echo "[3/4] Staging Flatpak application files..."
rm -rf "$STAGE_DIR" "$REPO_DIR"
flatpak build-init "$STAGE_DIR" "$APP_ID" org.gnome.Platform org.gnome.Platform "$RUNTIME_VER"

APP_FILES="${STAGE_DIR}/files"
mkdir -p "${APP_FILES}/bin" \
         "${APP_FILES}/lib" \
         "${APP_FILES}/share/trad-rainmeter" \
         "${APP_FILES}/share/applications" \
         "${APP_FILES}/share/metainfo" \
         "${APP_FILES}/share/icons/hicolor/scalable/apps" \
         "${APP_FILES}/share/icons/hicolor/512x512/apps"

install -m755 build/rainmeter-native "${APP_FILES}/bin/rainmeter-native"
install -m755 build/rmskin-unpacker "${APP_FILES}/bin/rmskin-unpacker"
install -m755 launcher_gui.py "${APP_FILES}/share/trad-rainmeter/launcher_gui.py"
cp -r assets suites widgets community gnome-extension "${APP_FILES}/share/trad-rainmeter/"

cat > "${APP_FILES}/bin/trad-rainmeter-gui" <<'EOF'
#!/usr/bin/env sh
export LD_LIBRARY_PATH="/app/lib:${LD_LIBRARY_PATH:-}"
exec python3 /app/share/trad-rainmeter/launcher_gui.py "$@"
EOF
chmod 755 "${APP_FILES}/bin/trad-rainmeter-gui"

install -m644 flatpak/com.github.kiddzhasi.TradRainmeter.desktop \
  "${APP_FILES}/share/applications/${APP_ID}.desktop"
install -m644 flatpak/com.github.kiddzhasi.TradRainmeter.metainfo.xml \
  "${APP_FILES}/share/metainfo/${APP_ID}.metainfo.xml"
install -m644 assets/trad-engine.png \
  "${APP_FILES}/share/icons/hicolor/512x512/apps/${APP_ID}.png"

# Bundle any shared libraries required by rainmeter-native not present in org.gnome.Platform
RUNTIME_LIB_SYS="/var/lib/flatpak/runtime/org.gnome.Platform/x86_64/${RUNTIME_VER}/active/files/lib/x86_64-linux-gnu"
RUNTIME_LIB_USR="${HOME}/.local/share/flatpak/runtime/org.gnome.Platform/x86_64/${RUNTIME_VER}/active/files/lib/x86_64-linux-gnu"

for so in $(ldd build/rainmeter-native build/rmskin-unpacker | awk '/=> \// {print $3}' | sort -u); do
  base="$(basename "$so")"
  if [ ! -e "${RUNTIME_LIB_SYS}/${base}" ] && [ ! -e "${RUNTIME_LIB_USR}/${base}" ]; then
    cp -L "$so" "${APP_FILES}/lib/${base}"
  fi
done

flatpak build-finish "$STAGE_DIR" \
  --command=trad-rainmeter-gui \
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
  --filesystem=xdg-cache/trad-rainmeter:create \
  --filesystem=xdg-download:ro

# 4. Export single-file .flatpak bundle
echo "[4/4] Exporting single-file Flatpak bundle to ${BUNDLE_FILE}..."
mkdir -p "$OUT_DIR"
flatpak build-export "$REPO_DIR" "$STAGE_DIR"
flatpak build-bundle "$REPO_DIR" "$BUNDLE_FILE" "$APP_ID"
rm -rf "$STAGE_DIR" "$REPO_DIR"

echo "================================================================"
echo "✅ Flatpak bundle created: ${BUNDLE_FILE}"
echo "   Install with: flatpak install --user -y ${BUNDLE_FILE}"
echo "   Run with:     flatpak run ${APP_ID}"
echo "================================================================"

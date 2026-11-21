#!/usr/bin/env bash
set -euo pipefail

# Build a Debian / Ubuntu / Pop!_OS (.deb) APT package for Trad Desktop
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

VERSION="${1:-1.2.0}"
VERSION="${VERSION#v}"
ARCH="$(dpkg --print-architecture 2>/dev/null || echo amd64)"
PKG_NAME="trad-desktop_${VERSION}_${ARCH}"
PKG_ROOT="${ROOT_DIR}/dist/deb/${PKG_NAME}"

rm -rf "$PKG_ROOT"
mkdir -p "${PKG_ROOT}/DEBIAN" \
         "${PKG_ROOT}/usr/bin" \
         "${PKG_ROOT}/usr/share/trad-desktop" \
         "${PKG_ROOT}/usr/share/applications" \
         "${PKG_ROOT}/usr/share/icons/hicolor/scalable/apps" \
         "${PKG_ROOT}/usr/share/icons/hicolor/512x512/apps" \
         "${PKG_ROOT}/usr/share/gnome-shell/extensions"

cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"

install -m755 build/rainmeter-native "${PKG_ROOT}/usr/bin/rainmeter-native"
install -m755 build/rmskin-unpacker "${PKG_ROOT}/usr/bin/rmskin-unpacker"

cp -r launcher_gui.py assets suites widgets community gnome-extension "${PKG_ROOT}/usr/share/trad-desktop/"
chmod 755 "${PKG_ROOT}/usr/share/trad-desktop/launcher_gui.py"

cat > "${PKG_ROOT}/usr/bin/trad-desktop" <<'EOF'
#!/usr/bin/env bash
exec python3 /usr/share/trad-desktop/launcher_gui.py "$@"
EOF
chmod 755 "${PKG_ROOT}/usr/bin/trad-desktop"
ln -sf trad-desktop "${PKG_ROOT}/usr/bin/trad-rainmeter"

install -m644 assets/trad-engine.svg "${PKG_ROOT}/usr/share/icons/hicolor/scalable/apps/trad-engine.svg"
install -m644 assets/trad-engine.png "${PKG_ROOT}/usr/share/icons/hicolor/512x512/apps/trad-engine.png"

cat > "${PKG_ROOT}/usr/share/applications/trad-desktop.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Trad Desktop
Comment=Trad Desktop Widgets, Suites, Themes, Music Players & Visualizers
Exec=/usr/bin/trad-desktop
Icon=trad-engine
Terminal=false
Categories=Utility;DesktopSettings;
EOF

# Install GNOME extension system-wide so Extension Manager detects it automatically
if [ -d "gnome-extension/trad-desktop@kiddzhasi.github.com" ]; then
  cp -r gnome-extension/trad-desktop@kiddzhasi.github.com \
        "${PKG_ROOT}/usr/share/gnome-shell/extensions/trad-desktop@kiddzhasi.github.com"
fi

INSTALLED_SIZE="$(du -sk "$PKG_ROOT" | awk '{print $1}')"

cat > "${PKG_ROOT}/DEBIAN/control" <<EOF
Package: trad-desktop
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Replaces: trad-rainmeter
Conflicts: trad-rainmeter
Maintainer: KidDzhasi <tmadzhasi@gmail.com>
Homepage: https://github.com/KidDzhasi/Trad-Desktop
Installed-Size: ${INSTALLED_SIZE}
Depends: libc6, libstdc++6, libwayland-client0, libwayland-egl1, libx11-6, libxrandr2, libegl1, libepoxy0, libfontconfig1, libzip4t64 | libzip4, libcurl4t64 | libcurl4, liblua5.4-0 | liblua5.3-0, libglib2.0-0t64 | libglib2.0-0, libdbus-1-3, libpulse0, python3 (>= 3.10), python3-gi, python3-gi-cairo, gir1.2-gtk-4.0, gir1.2-adw-1
Description: Trad Desktop — Native Linux Desktop Widgets & Themes
 Hardware-accelerated desktop widget engine for Wayland and X11/XWayland
 desktop environments (GNOME, Pop!_OS, Ubuntu, Fedora). Includes suites, Basic Widgets
 with themes/shapes/designs, live Open-Meteo & met.no weather with village search,
 MPRIS music players, real-time PulseAudio/PipeWire visualizers, and a GTK4 Control Center.
EOF

cat > "${PKG_ROOT}/DEBIAN/postinst" <<'EOF'
#!/usr/bin/env sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f /usr/share/icons/hicolor || true
fi
exit 0
EOF
chmod 644 "${PKG_ROOT}/DEBIAN/control"
chmod 755 "${PKG_ROOT}/DEBIAN/postinst"
find "$PKG_ROOT" -type d -exec chmod 0755 {} +

mkdir -p "${ROOT_DIR}/dist"
dpkg-deb --build --root-owner-group "$PKG_ROOT" "${ROOT_DIR}/dist/${PKG_NAME}.deb"
echo "Built APT package: ${ROOT_DIR}/dist/${PKG_NAME}.deb"

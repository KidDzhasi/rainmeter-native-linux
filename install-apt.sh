#!/usr/bin/env bash
set -euo pipefail

# Trad Desktop — Automated APT Installer for Pop!_OS, Ubuntu, Debian & Linux Mint
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== [1/4] Installing APT build & runtime dependencies ==="
sudo apt-get update
sudo apt-get install -y \
    build-essential cmake pkg-config git \
    wayland-protocols libwayland-dev libxkbcommon-dev \
    libx11-dev libxrandr-dev \
    libegl-dev libgles-dev libepoxy-dev \
    libfontconfig-dev libzip-dev libcurl4-openssl-dev \
    libglib2.0-dev libdbus-1-dev libpulse-dev \
    python3 python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 \
    desktop-file-utils

if ! apt-cache show liblua5.4-dev >/dev/null 2>&1 || ! sudo apt-get install -y liblua5.4-dev; then
    sudo apt-get install -y liblua5.3-dev
fi

echo "=== [2/4] Compiling Trad Desktop C++ engine ==="
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"

echo "=== [3/4] Installing binaries, desktop assets, suites & widgets system-wide ==="
sudo rm -rf /usr/share/trad-rainmeter /usr/bin/trad-rainmeter /usr/share/applications/trad-rainmeter.desktop
sudo install -Dm755 build/rainmeter-native /usr/bin/rainmeter-native
sudo install -Dm755 build/rmskin-unpacker /usr/bin/rmskin-unpacker

sudo mkdir -p /usr/share/trad-desktop
sudo cp -r launcher_gui.py assets suites widgets community gnome-extension /usr/share/trad-desktop/
sudo chmod +x /usr/share/trad-desktop/launcher_gui.py

sudo tee /usr/bin/trad-desktop >/dev/null <<'EOF'
#!/usr/bin/env bash
exec python3 /usr/share/trad-desktop/launcher_gui.py "$@"
EOF
sudo chmod +x /usr/bin/trad-desktop
sudo ln -sf /usr/bin/trad-desktop /usr/bin/trad-rainmeter

sudo install -Dm644 assets/trad-engine.svg /usr/share/icons/hicolor/scalable/apps/trad-engine.svg
sudo install -Dm644 assets/trad-engine.png /usr/share/icons/hicolor/512x512/apps/trad-engine.png

sudo tee /usr/share/applications/trad-desktop.desktop >/dev/null <<'EOF'
[Desktop Entry]
Type=Application
Name=Trad Desktop
Comment=Trad Desktop Widgets, Suites, Themes, Music Players & Visualizers
Exec=/usr/bin/trad-desktop
Icon=trad-engine
Terminal=false
Categories=Utility;DesktopSettings;
EOF

sudo update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
sudo gtk-update-icon-cache -f /usr/share/icons/hicolor >/dev/null 2>&1 || true

echo "=== [4/4] Installing GNOME Shell extension (optional) ==="
EXT_ZIP="gnome-extension/trad-desktop@kiddzhasi.github.com.shell-extension.zip"
if command -v gnome-extensions >/dev/null 2>&1 && [ -f "$EXT_ZIP" ]; then
    gnome-extensions install --force "$EXT_ZIP" || true
    echo "GNOME extension installed. Log out and back in, then enable 'Trad Desktop' in Extension Manager."
fi

echo ""
echo "Installation complete! Launch 'Trad Desktop' from your Applications menu or run: trad-desktop"

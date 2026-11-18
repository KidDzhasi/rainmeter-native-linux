#!/usr/bin/env bash
# =============================================================================
# Trad Rainmeter — Flatpak Bundle Builder
# Builds and exports dist/trad-rainmeter.flatpak for easy one-file installation:
#   flatpak install --user dist/trad-rainmeter.flatpak
# =============================================================================
set -euo pipefail

APP_ID="com.github.kiddzhasi.TradRainmeter"
MANIFEST="flatpak/${APP_ID}.yml"
BUILD_DIR="build-flatpak"
REPO_DIR="flatpak-repo"
OUT_DIR="dist"
BUNDLE_FILE="${OUT_DIR}/trad-rainmeter.flatpak"

echo "================================================================"
echo "  Building Flatpak Bundle: ${BUNDLE_FILE}"
echo "================================================================"

if ! command -v flatpak-builder >/dev/null 2>&1; then
  echo "Error: 'flatpak-builder' is not installed."
  echo "  • On Fedora: sudo dnf install -y flatpak flatpak-builder"
  echo "  • On Ubuntu/Pop!_OS/Debian: sudo apt install -y flatpak flatpak-builder"
  exit 1
fi

flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo

echo "[1/3] Ensuring org.gnome.Platform//47 and org.gnome.Sdk//47 are installed..."
flatpak install --user -y flathub org.gnome.Platform//47 org.gnome.Sdk//47

echo "[2/3] Running flatpak-builder..."
flatpak-builder --user --force-clean --repo="${REPO_DIR}" "${BUILD_DIR}" "${MANIFEST}"

echo "[3/3] Exporting single-file Flatpak bundle to ${BUNDLE_FILE}..."
mkdir -p "${OUT_DIR}"
flatpak build-bundle "${REPO_DIR}" "${BUNDLE_FILE}" "${APP_ID}"

echo "================================================================"
echo "✅ Flatpak bundle created: ${BUNDLE_FILE}"
echo "   Install with: flatpak install --user ${BUNDLE_FILE}"
echo "   Run with:     flatpak run ${APP_ID}"
echo "================================================================"

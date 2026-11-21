# Trad Desktop

A lightweight, hardware-accelerated native desktop widget engine and GNOME Shell companion (`trad-desktop@kiddzhasi.github.com`) for Linux (Wayland, XWayland, X11 — Pop!\_OS, Ubuntu, Debian, Linux Mint, Fedora) and Windows 10 / 11.

## Highlights

- **GNOME Wayland / Mutter, Pop!\_OS, Cosmic, Layer-Shell & Windows Compatible:** Pins widgets cleanly to the desktop background beneath normal application windows, with per-monitor positioning, fractional scaling, and automatic resolution fitting (`AutoFit`).
- **Trad Desktop Control Center (`launcher_gui.py` & `windows/trad_desktop_win.py`):** Native GTK4 / Libadwaita (Linux) and matching dark Control Center (Windows) featuring:
  - **Suites Tab:** One-click suite switching (`TradSunset`, `Trad Cyber`, `DashboardSuite`, `TealMountainSuite`, `GreenRibbonSuite`, plus user-saved custom suites).
  - **Basic Widgets & Theme Studio:** 8 modular anchored system widgets (`BasicClock`, `BasicDate`, `BasicWeather`, `BasicCpu`, `BasicRamSwap`, `BasicNet`, `BasicDisks`, `BasicStorage`) with **10 Color Themes**, **6 Card Shapes**, and **4 Widget Design Styles**.
  - **Live Weather & Village Search (`Open-Meteo` + `met.no` Fallback):** Live weather widgets and interactive 24-hour + 7-day forecast popup on click, with multi-source search for cities, towns, and rural villages (plus custom coordinate entry).
  - **Music Players & Audio Visualizers:** Live media player widgets (`MusicBanner`, `MusicMinimal`, `MusicCompact`) and real-time FFT spectrum visualizers (`AudioVisualizer`, `AudioHorizon`).
  - **Widgets & Position Studio:** Interactive multi-widget monitor canvas, skin installer, widget uninstaller, and custom Suite Builder.
- **GNOME Shell Extension (`gnome-extension/trad-desktop@kiddzhasi.github.com`):** Top-bar indicator for GNOME 45–51 compatible with GNOME Extension Manager and `extensions.gnome.org`.

---

## Installation

### Pop!\_OS / Ubuntu / Debian / Linux Mint (APT)

**Option A — Install the `.deb` package with `apt` (Recommended):**
Download `trad-desktop_<version>_amd64.deb` from [GitHub Releases](https://github.com/KidDzhasi/Trad-Desktop/releases) and install with `apt`:

```bash
sudo apt update
sudo apt install ./trad-desktop_*_amd64.deb
trad-desktop
```

**Option B — Build & install from source via `./install-apt.sh`:**

```bash
git clone https://github.com/KidDzhasi/Trad-Desktop.git
cd Trad-Desktop
chmod +x install-apt.sh
./install-apt.sh
```

Or build the `.deb` locally yourself:

```bash
chmod +x scripts/build-deb.sh
./scripts/build-deb.sh 1.2.0
sudo apt install ./dist/trad-desktop_1.2.0_*.deb
```

### Fedora / DNF

```bash
sudo dnf install cmake gcc-c++ pkgconf-pkg-config wayland-devel wayland-protocols-devel \
  libxkbcommon-devel libX11-devel libXrandr-devel mesa-libEGL-devel libepoxy-devel \
  fontconfig-devel libzip-devel libcurl-devel lua-devel glib2-devel dbus-devel \
  pulseaudio-libs-devel python3-gobject gtk4 libadwaita
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"
python3 ./launcher_gui.py
```

### Flatpak (All Linux Distros)

Build and install the single-file `.flatpak` bundle (`com.github.kiddzhasi.TradDesktop`):

```bash
chmod +x scripts/build-flatpak.sh
./scripts/build-flatpak.sh
flatpak install --user dist/trad-desktop.flatpak
flatpak run com.github.kiddzhasi.TradDesktop
```

### Windows 10 & Windows 11 (Standalone `.exe` + Skin Package)

1. **Standalone Windows App (`TradDesktop-Windows-x64.exe`):**
   - Download `TradDesktop-Windows-x64.exe` (or `TradDesktop-Windows-Portable-x64.zip`) from GitHub Actions / Releases, or build locally on Windows via `windows\build-windows-exe.bat`.
   - Includes the Win32 pinned desktop widget engine (`HWND_BOTTOM`), 3-tab Control Center, 10 Themes, 6 Shapes, 4 Designs, Music Players, Audio Visualizers, and Live Village Weather Forecast.
2. **Exportable Skin Package (`TradDesktop_1.2.0.rmskin`):**
   - Double-click `TradDesktop_1.2.0.rmskin` on Windows (or generate it via `python windows/build_rmskin.py`).
   - See [windows/README-WINDOWS.md](windows/README-WINDOWS.md) for full details.

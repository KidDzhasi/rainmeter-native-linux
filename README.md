# Trad Rainmeter

A lightweight, hardware-accelerated native Linux desktop widget engine and GNOME Shell companion (`trad-rainmeter@kiddzhasi.github.com`) for Wayland, XWayland, and X11 desktop environments (Pop!\_OS, Ubuntu, Debian, Linux Mint, Fedora).

## Highlights

- **GNOME Wayland / Mutter, Pop!\_OS, Cosmic & Layer-Shell Compatible:** Pins widgets cleanly to the desktop background beneath normal application windows, with per-monitor positioning, fractional scaling, and automatic resolution fitting (`AutoFit`).
- **Trad Rainmeter Control Center (`launcher_gui.py`):** Native GTK4 / Libadwaita application featuring:
  - **Suites Tab:** One-click suite switching (`TradSunset`, `DashboardSuite`, `TealMountainSuite`, `GreenRibbonSuite`, plus user-saved custom suites).
  - **Basic Widgets & Theme Studio:** 8 modular anchored system widgets (`BasicClock`, `BasicDate`, `BasicWeather`, `BasicCpu`, `BasicRamSwap`, `BasicNet`, `BasicDisks`, `BasicStorage`) with **10 Color Themes**, **6 Card Shapes**, and **4 Widget Design Styles**.
  - **Live Weather & Village Search (`Open-Meteo` + `met.no` Fallback):** Live weather widgets and interactive 24-hour + 7-day forecast popup on click, with multi-source search for cities, towns, and rural villages (plus custom coordinate entry).
  - **Music Players & Audio Visualizers:** Live MPRIS2 D-Bus media player widgets (`MusicBanner`, `MusicMinimal`, `MusicCompact`) and real-time PulseAudio / PipeWire FFT spectrum visualizers (`AudioVisualizer`, `AudioHorizon`).
  - **Widgets & Position Studio:** Interactive multi-widget monitor canvas, `.rmskin` / `.ini` installer, widget uninstaller, and custom Suite Builder.
- **GNOME Shell Extension (`gnome-extension/trad-rainmeter@kiddzhasi.github.com`):** Top-bar indicator for GNOME 45–51 compatible with GNOME Extension Manager and `extensions.gnome.org`.

---

## Installation

### Pop!\_OS / Ubuntu / Debian / Linux Mint (APT)

**Option A — Install the `.deb` package with `apt` (Recommended):**
Download `trad-rainmeter_<version>_amd64.deb` from [GitHub Releases](https://github.com/KidDzhasi/Trad-rainmeter/releases) and install with `apt` (which resolves all dependencies automatically):

```bash
sudo apt update
sudo apt install ./trad-rainmeter_*_amd64.deb
trad-rainmeter
```

**Option B — Build & install from source via `./install-apt.sh`:**

```bash
git clone https://github.com/KidDzhasi/Trad-rainmeter.git
cd Trad-rainmeter
chmod +x install-apt.sh
./install-apt.sh
```

Or build the `.deb` locally yourself:

```bash
chmod +x scripts/build-deb.sh
./scripts/build-deb.sh 1.1.0
sudo apt install ./dist/trad-rainmeter_1.1.0_*.deb
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

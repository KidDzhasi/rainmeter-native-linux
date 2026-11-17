# Trad Rainmeter

A lightweight, hardware-accelerated native Linux desktop widget engine and GNOME Shell companion (`trad-rainmeter@kiddzhasi.github.com`) for Wayland and XWayland desktop environments.

## Highlights

- **GNOME Wayland / Mutter & Layer-Shell Compatible:** Pins widgets cleanly to the desktop background beneath normal application windows, with per-monitor positioning, fractional scaling, and automatic resolution fitting (`AutoFit`).
- **Trad Rainmeter Control Center (`launcher_gui.py`):** Native GTK4 / Libadwaita application featuring:
  - **Suites Tab:** One-click suite switching (`TradSunset`, `DashboardSuite`, `TealMountainSuite`, `GreenRibbonSuite`, plus user-saved custom suites).
  - **Basic Widgets & Theme Studio:** 8 modular anchored system widgets (`BasicClock`, `BasicDate`, `BasicWeather`, `BasicCpu`, `BasicRamSwap`, `BasicNet`, `BasicDisks`, `BasicStorage`) with **10 Color Themes** (`Neon Blue`, `Frosted Glass`, `Pure Transparent`, `Arctic Blue`, `Fedora Cyber`, `Crystal Aqua Glass`, `Sunset Glow`, `Sapphire & Amber`, `Crimson Night Drive`, `Obsidian Lime`), **6 Card Shapes** (`Rounded Card`, `Sharp Box`, `Soft Squircle`, `Full Pill / Capsule`, `Circular Disc`, `Floating Borderless`), and **4 Widget Design Styles** (`Vertical Bars`, `Circular Ring Gauges`, `Capsule Pill`, `Horizontal Minimal`).
  - **Music Players & Audio Visualizers:** Live MPRIS2 D-Bus media player widgets (`MusicBanner`, `MusicMinimal`, `MusicCompact`) and real-time PulseAudio / PipeWire FFT spectrum visualizers (`AudioVisualizer`, `AudioHorizon`).
  - **Widgets & Position Studio:** Interactive multi-widget monitor canvas, `.rmskin` / `.ini` installer, widget uninstaller, and custom Suite Builder.
- **GNOME Shell Extension (`gnome-extension/trad-rainmeter@kiddzhasi.github.com`):** Top-bar indicator for GNOME 45–51 compatible with GNOME Extension Manager and `extensions.gnome.org`.

## Quick Start

```bash
cmake -B build
cmake --build build -j4
python3 ./launcher_gui.py
```

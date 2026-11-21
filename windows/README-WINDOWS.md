# Trad Desktop for Windows

Trad Desktop for Windows provides a standalone Windows 10 / 11 desktop widget engine + Control Center `.exe` (plus exportable `.rmskin` skin packages).

---

## 1. Standalone Windows App (`TradDesktop-Windows-x64.exe`)

Runs all Trad Desktop suites and widgets directly on Windows 10 & Windows 11:

- **Pinned Desktop Wallpaper Layer (`HWND_BOTTOM`):** Widgets are pinned to the desktop background (`WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE`), hidden from the Windows Taskbar and `Alt+Tab`, and locked in place so accidental clicks or drags on the desktop never move them.
- **3-Tab Control Center GUI (Matching the Linux GTK4 / Libadwaita Interface):**
  1. **Suites Tab:** One-click switching between `TradSunset`, `Trad Cyber`, `DashboardSuite`, `GreenRibbonSuite`, and custom saved suites.
  2. **Basic Widgets Tab:**
     - **10 Color Themes**, **6 Card Shapes**, and **4 Gauge Designs** with live 4-card Swatch Preview Strip
     - **8 Core Telemetry Widgets** (`BasicClock`, `BasicDate`, `BasicWeather`, `BasicCpu`, `BasicRamSwap`, `BasicNet`, `BasicDisks`, `BasicStorage`)
     - **3 Media Players & 2 Audio Visualizers** (`MusicBanner`, `MusicMinimal`, `MusicCompact`, `AudioVisualizer`, `AudioHorizon`) with native Win32 Media Key controls
     - **Weather Location & Saved Villages Manager**
  3. **Widgets & Position Tab:** Interactive multi-widget monitor canvas, skin installer, Custom Suite Builder, and one-click `.rmskin` exporter.
- **Live Expandable Weather Forecast & Rural Village Search:**
  - Click any weather widget (or click **Full Forecast**) to open the 24-hour temperature curve + 7-day forecast popup.
  - Multi-source geocoder (**ArcGIS World Geocoder + Open-Meteo**) finds both major cities and rural villages (e.g. `Mahatlani, Vhembe, Limpopo`, `Majosi`, `Masakona`), with automatic fallback from Open-Meteo to the **Norwegian Meteorological Institute (`api.met.no`)**.

---

## 2. Building on Windows from Source

```bat
git clone https://github.com/KidDzhasi/Trad-Desktop.git
cd Trad-Desktop
windows\build-windows-exe.bat
```

Or run directly with Python 3.10+ on Windows:

```bat
pip install psutil
python windows\trad_desktop_win.py
```

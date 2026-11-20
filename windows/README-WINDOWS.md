# Trad Rainmeter for Windows (`windows-port`)

Trad Rainmeter for Windows provides **both** a standalone Windows desktop widget engine + Control Center `.exe` **and** a genuine `.rmskin` installer package for classic Windows Rainmeter 4.5+.

---

## 1. Standalone Windows App (`TradRainmeter-Windows-x64.exe`)

Runs all Trad Rainmeter suites and widgets directly on Windows 10 & Windows 11 **without** needing classic Rainmeter installed:

- **Pinned Desktop Wallpaper Layer (`HWND_BOTTOM`):** Widgets are pinned to the desktop background (`WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE`), hidden from the Windows Taskbar and `Alt+Tab`, and locked in place so accidental clicks or drags on the desktop never move them.
- **3-Tab Control Center GUI:**
  1. **Suites Tab:** One-click switching between `TradSunset`, `Trad Cyber`, `DashboardSuite`, `GreenRibbonSuite`, and custom saved suites.
  2. **Basic Widgets & Weather Tab:**
     - **10 Color Themes**, **6 Card Shapes**, and **4 Gauge Designs**
     - **8 Core Telemetry Widgets** (`BasicClock`, `BasicDate`, `BasicWeather`, `BasicCpu`, `BasicRamSwap`, `BasicNet`, `BasicDisks`, `BasicStorage`)
     - **3 Media Players & 2 Audio Visualizers** (`MusicBanner`, `MusicMinimal`, `MusicCompact`, `AudioVisualizer`, `AudioHorizon`) with native Win32 Media Key controls (`VK_MEDIA_PLAY_PAUSE`, `VK_MEDIA_NEXT_TRACK`, `VK_MEDIA_PREV_TRACK`)
  3. **Widgets & Position Tab:** Interactive multi-widget monitor canvas, `.rmskin` / `.ini` installer, and one-click `.rmskin` exporter.
- **Live Expandable Weather Forecast & Rural Village Search:**
  - Click any weather widget (or click **Weather Forecast & Villages**) to open the 24-hour temperature curve + 7-day forecast popup.
  - Multi-source geocoder (**ArcGIS World Geocoder + Open-Meteo**) finds both major cities and rural villages (e.g. `Mahatlani, Vhembe, Limpopo`, `Majosi`, `Masakona`), with automatic fallback from Open-Meteo to the **Norwegian Meteorological Institute (`api.met.no`)**.

---

## 2. Classic Windows Rainmeter Package (`TradRainmeter_1.1.0.rmskin`)

If you also use classic [Rainmeter for Windows](https://www.rainmeter.net/):

1. Double-click **`TradRainmeter_1.1.0.rmskin`** (located in `dist/` or exported from the Control Center via **Export .rmskin for Windows Rainmeter**).
2. Windows Rainmeter's `SkinInstaller.exe` will open the package banner and install all Trad Suites and Basic Widgets into `Documents\Rainmeter\Skins\TradRainmeter\`.

---

## 3. Building on Windows from Source

```bat
git clone -b windows-port https://github.com/KidDzhasi/rainmeter-native-linux.git
cd rainmeter-native-linux
windows\build-windows-exe.bat
```

Or run directly with Python 3.10+ on Windows:

```bat
pip install psutil
python windows\trad_rainmeter_win.py
```

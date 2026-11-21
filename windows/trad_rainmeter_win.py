#!/usr/bin/env python3
"""
Trad Desktop for Windows — Standalone Desktop Widget Engine & Control Center
Faithfully mirrors the Linux GTK4 / Libadwaita Control Center interface & features:
  • Libadwaita-Dark Inspired Header Bar & 3-Tab Switcher:
      1. Suites: Target Monitor, Built-in & Custom Saved Suites (with Edit & Delete)
      2. Basic Widgets: Theme/Shape/Design Studio with live Swatch Preview Strip &
         10 Quick-Pick Themes, Music Players & Visualizers, Full Weather Location &
         Rural Village Manager (Search + Manual Coords + Saved Locations), and Core 8
         Anchored Telemetry Widgets.
      3. Widgets & Position: Split view with Custom & Active Widgets list, Custom Suite
         Builder, Apply & Reload button, Interactive Multi-Widget Monitor Canvas,
         9 Quick Anchors, Monitor/AutoFit/Manual Scale, and Custom X/Y Pixel Offsets.
  • Pinned Desktop Wallpaper Layer Engine (HWND_BOTTOM, WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
    strictly non-draggable on desktop).
  • Clickable 24-Hour & 7-Day Weather Forecast Popup (--weather-popup).
  • 1-Click .rmskin Package Installer & Windows Rainmeter .rmskin Exporter.
"""

import concurrent.futures
import configparser
import ctypes
from ctypes import wintypes
import datetime
import json
import math
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import urllib.parse
import urllib.request
import zipfile

# Enable Per-Monitor DPI awareness on Windows 10/11 for sharp text & graphics
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

if getattr(sys, "frozen", False):
    REPO_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    REPO_DIR = os.path.dirname(SCRIPT_DIR)
    APP_DIR = REPO_DIR

if sys.platform == "win32":
    APPDATA_BASE = os.environ.get("APPDATA", os.path.expanduser("~"))
    LOCALAPPDATA_BASE = os.environ.get("LOCALAPPDATA", APPDATA_BASE)
    CONFIG_DIR = os.path.join(APPDATA_BASE, "TradDesktop")
    CACHE_DIR = os.path.join(LOCALAPPDATA_BASE, "TradDesktop", "cache")
else:
    CONFIG_DIR = os.path.expanduser("~/.config/rainmeter-native")
    CACHE_DIR = os.path.expanduser("~/.cache/trad-desktop")

os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

USER_SKINS_DIR = os.path.join(CONFIG_DIR, "Skins")
GLOBAL_CONFIG = os.path.join(CONFIG_DIR, "Rainmeter.ini")
WEATHER_LOCATIONS_PATH = os.path.join(CONFIG_DIR, "weather_locations.json")

SYSTEM_SUITES_DIR = os.path.join(REPO_DIR, "suites")
SYSTEM_WIDGETS_DIR = os.path.join(REPO_DIR, "widgets")

WIDGETS_DIR = os.path.join(CONFIG_DIR, "widgets")
if os.path.isdir(SYSTEM_WIDGETS_DIR) and not os.path.isdir(WIDGETS_DIR):
    shutil.copytree(SYSTEM_WIDGETS_DIR, WIDGETS_DIR, dirs_exist_ok=True)
elif not os.path.isdir(WIDGETS_DIR):
    WIDGETS_DIR = SYSTEM_WIDGETS_DIR

SUITES_DIR = os.path.join(CONFIG_DIR, "suites")
if os.path.isdir(SYSTEM_SUITES_DIR) and not os.path.isdir(SUITES_DIR):
    shutil.copytree(SYSTEM_SUITES_DIR, SUITES_DIR, dirs_exist_ok=True)
elif not os.path.isdir(SUITES_DIR):
    SUITES_DIR = SYSTEM_SUITES_DIR

THEME_INC_PATH = os.path.join(WIDGETS_DIR, "Theme.inc")
WEATHER_INC_PATH = os.path.join(WIDGETS_DIR, "Weather.inc")
USER_THEME_INC = os.path.join(CONFIG_DIR, "Theme.inc")
USER_WEATHER_INC = os.path.join(CONFIG_DIR, "Weather.inc")

try:
    from windows.build_rmskin import build_rmskin_package
except ImportError:
    try:
        from build_rmskin import build_rmskin_package
    except ImportError:
        build_rmskin_package = None

try:
    import psutil
except ImportError:
    psutil = None

# ---------------------------------------------------------------------------
# Color Palette (Matching GTK4 / Libadwaita Adwaita-Dark + Purple Theme)
# ---------------------------------------------------------------------------
UI_BG = "#1E1B24"
UI_HEADER_BG = "#24212C"
UI_CARD_BG = "#2A2634"
UI_CARD_ALT = "#312C3C"
UI_CARD_HOVER = "#373244"
UI_SELECTED_ROW = "#42335C"
UI_BORDER = "#3B3648"
UI_DIVIDER = "#211E28"
UI_CANVAS_BG = "#141822"
UI_TEXT = "#F8FAFC"
UI_DIM = "#9E98AD"
UI_PURPLE = "#8B3DFF"
UI_PURPLE_HOVER = "#9C5AFF"
UI_RED_BG = "#4D232C"
UI_RED_FG = "#FF8090"
UI_GREEN_FG = "#34D399"
UI_CYAN = "#22D3EE"
UI_AMBER = "#FFB703"

# ---------------------------------------------------------------------------
# Theme, Shape & Design Catalog (100% Parity with Linux Control Center)
# ---------------------------------------------------------------------------
BASIC_WIDGET_THEMES = [
    {
        "name": "Neon Blue (GNOME Edge)",
        "subtitle": "Matte carbon black with glowing electric blue border and cyan-blue bars",
        "corner_radius": 8,
        "bg_fill": "Fill LinearGradient 135 | 14,18,28,235 | 6,8,14,245",
        "border_stroke": "StrokeWidth 2 | Stroke Color 0,175,255,235",
        "accent": "0,195,255,255",
        "text": "240,248,255,255",
        "bg_hex": "#0E121C",
        "border_hex": "#00AFFF",
        "accent_hex": "#00C3FF",
    },
    {
        "name": "Frosted Glass (Default)",
        "subtitle": "Translucent dark slate glass with subtle white border and cyan accent",
        "corner_radius": 8,
        "bg_fill": "Fill LinearGradient 135 | 28,36,52,190 | 14,18,26,210",
        "border_stroke": "StrokeWidth 1.5 | Stroke Color 255,255,255,55",
        "accent": "0,210,255,255",
        "text": "255,255,255,255",
        "bg_hex": "#1C2434",
        "border_hex": "#5C6675",
        "accent_hex": "#00D2FF",
    },
    {
        "name": "Pure Transparent",
        "subtitle": "Zero background box or border — clean floating text and bars directly on wallpaper",
        "corner_radius": 8,
        "bg_fill": "Fill Color 0,0,0,0",
        "border_stroke": "StrokeWidth 0 | Stroke Color 0,0,0,0",
        "accent": "0,220,255,255",
        "text": "255,255,255,255",
        "bg_hex": "#12151E",
        "border_hex": "#2A3040",
        "accent_hex": "#00DCFF",
    },
    {
        "name": "Arctic Blue (Nordic Frost)",
        "subtitle": "Deep polar navy glass with ice-blue rim and frost-cyan telemetry bars",
        "corner_radius": 10,
        "bg_fill": "Fill LinearGradient 135 | 22,34,56,215 | 12,20,34,230",
        "border_stroke": "StrokeWidth 1.5 | Stroke Color 120,200,255,140",
        "accent": "136,192,208,255",
        "text": "236,239,244,255",
        "bg_hex": "#162238",
        "border_hex": "#78C8FF",
        "accent_hex": "#88C0D0",
    },
    {
        "name": "Fedora Cyber (Magenta & Cyan)",
        "subtitle": "Deep cyber-violet glass with neon magenta border and glowing cyan bars",
        "corner_radius": 10,
        "bg_fill": "Fill LinearGradient 135 | 26,14,46,225 | 12,8,24,240",
        "border_stroke": "StrokeWidth 2 | Stroke Color 235,0,255,200",
        "accent": "0,245,212,255",
        "text": "250,245,255,255",
        "bg_hex": "#1A0E2E",
        "border_hex": "#EB00FF",
        "accent_hex": "#00F5D4",
    },
    {
        "name": "Crystal Aqua Glass",
        "subtitle": "Tropical turquoise lagoon glass with bright aqua-mint telemetry",
        "corner_radius": 12,
        "bg_fill": "Fill LinearGradient 135 | 60,90,125,135 | 30,50,75,155",
        "border_stroke": "StrokeWidth 1.5 | Stroke Color 180,235,255,150",
        "accent": "64,224,208,255",
        "text": "255,255,255,255",
        "bg_hex": "#284159",
        "border_hex": "#9CE5FF",
        "accent_hex": "#2EE8C8",
    },
    {
        "name": "Sunset Glow (Amber & Coral)",
        "subtitle": "Warm dusk plum glass with golden-amber border and sunset coral accents",
        "corner_radius": 10,
        "bg_fill": "Fill LinearGradient 135 | 44,18,38,225 | 20,10,22,240",
        "border_stroke": "StrokeWidth 1.5 | Stroke Color 255,165,50,190",
        "accent": "255,183,3,255",
        "text": "255,248,240,255",
        "bg_hex": "#2C1226",
        "border_hex": "#FFA532",
        "accent_hex": "#FFB703",
    },
    {
        "name": "Sapphire and Amber",
        "subtitle": "Midnight sapphire cards with warm golden-orange gauges and borders",
        "corner_radius": 8,
        "bg_fill": "Fill LinearGradient 135 | 15,25,48,235 | 8,14,28,245",
        "border_stroke": "StrokeWidth 1.5 | Stroke Color 245,158,11,195",
        "accent": "251,146,60,255",
        "text": "248,250,252,255",
        "bg_hex": "#0F1930",
        "border_hex": "#F59E0B",
        "accent_hex": "#FB923C",
    },
    {
        "name": "Crimson Night Drive",
        "subtitle": "Stealth obsidian carbon with crimson-red border and racing red telemetry",
        "corner_radius": 6,
        "bg_fill": "Fill LinearGradient 135 | 22,12,16,238 | 10,6,8,248",
        "border_stroke": "StrokeWidth 2 | Stroke Color 239,68,68,215",
        "accent": "248,113,113,255",
        "text": "255,245,245,255",
        "bg_hex": "#160C10",
        "border_hex": "#EF4444",
        "accent_hex": "#F87171",
    },
    {
        "name": "Obsidian Lime (Matrix Green)",
        "subtitle": "Dark terminal obsidian with neon emerald-lime border and hacker green bars",
        "corner_radius": 8,
        "bg_fill": "Fill LinearGradient 135 | 10,22,16,235 | 5,12,8,245",
        "border_stroke": "StrokeWidth 1.5 | Stroke Color 16,185,129,210",
        "accent": "52,211,153,255",
        "text": "236,253,245,255",
        "bg_hex": "#0A1610",
        "border_hex": "#10B981",
        "accent_hex": "#34D399",
    },
]

BASIC_WIDGET_SHAPES = [
    {"id": "rounded", "name": "Rounded Card (Default)", "subtitle": "Balanced 8–12px rounded rectangle card", "radius": None, "borderless": False},
    {"id": "sharp", "name": "Sharp Rectangular Box", "subtitle": "Crisp 0px sharp architectural corners", "radius": 0, "borderless": False},
    {"id": "squircle", "name": "Soft Squircle (20px)", "subtitle": "Smooth superellipse-style 20px corner curves", "radius": 20, "borderless": False},
    {"id": "pill", "name": "Full Pill / Capsule (36px)", "subtitle": "Deep stadium pill curvature (36px)", "radius": 36, "borderless": False},
    {"id": "circle", "name": "Circular / Oval Disc (80px)", "subtitle": "Ultra-round circular badge / oval gauge silhouette", "radius": 80, "borderless": False},
    {"id": "floating", "name": "Floating Borderless (HUD Only)", "subtitle": "Removes background box and border while keeping theme colors and gauges", "radius": 0, "borderless": True},
]

BASIC_WIDGET_DESIGNS = [
    {"id": "bars", "name": "Vertical Telemetry Bars (Classic)", "subtitle": "Vertical glowing telemetry bars and classic stacked typography"},
    {"id": "circular", "name": "Circular Ring Gauges (Radial)", "subtitle": "Glowing circular percentage rings and radial clock"},
    {"id": "pill", "name": "Compact Capsule Pill (Horizontal)", "subtitle": "Sleek horizontal progress bar and condensed HUD layout"},
    {"id": "minimal", "name": "Horizontal Minimal Typography", "subtitle": "Clean editorial typography with hairline horizontal dividers"},
]

DEFAULT_WEATHER_LOCATIONS = [
    {"name": "Johannesburg, South Africa", "lat": -26.2041, "lon": 28.0473},
    {"name": "Pretoria, South Africa", "lat": -25.7479, "lon": 28.2293},
    {"name": "Polokwane, Limpopo", "lat": -23.9045, "lon": 29.4689},
    {"name": "Giyani, Limpopo", "lat": -23.3025, "lon": 30.7187},
    {"name": "Mahatlani, Vhembe, Limpopo", "lat": -23.1643, "lon": 30.4832},
    {"name": "Cape Town, South Africa", "lat": -33.9249, "lon": 18.4241},
    {"name": "London, United Kingdom", "lat": 51.5074, "lon": -0.1278},
    {"name": "New York, USA", "lat": 40.7128, "lon": -74.0060},
]

# ---------------------------------------------------------------------------
# Custom Rounded Libadwaita UI Primitives for Tkinter
# ---------------------------------------------------------------------------
def draw_round_rect(canvas, x1, y1, x2, y2, r, **kwargs):
    r = max(0, min(r, (x2 - x1) / 2.0, (y2 - y1) / 2.0))
    if r <= 1:
        return canvas.create_rectangle(x1, y1, x2, y2, **kwargs)
    pts = [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1,
    ]
    return canvas.create_polygon(pts, smooth=True, **kwargs)


class PillSwitch(tk.Canvas):
    """GTK4 Adw.Switch lookalike pill toggle."""

    def __init__(self, parent, initial=False, command=None, bg=UI_CARD_BG):
        super().__init__(parent, width=44, height=24, bg=bg, highlightthickness=0, cursor="hand2")
        self._state = bool(initial)
        self._cmd = command
        self._draw()
        self.bind("<Button-1>", self._on_click)

    def _draw(self):
        self.delete("all")
        fill = UI_PURPLE if self._state else "#4A4658"
        draw_round_rect(self, 1, 2, 43, 22, 10, fill=fill, outline="")
        cx = 32 if self._state else 12
        self.create_oval(cx - 8, 4, cx + 8, 20, fill="#FFFFFF", outline="")

    def _on_click(self, _e=None):
        self._state = not self._state
        self._draw()
        if self._cmd:
            self._cmd(self._state)

    def get(self):
        return self._state

    def set(self, val):
        self._state = bool(val)
        self._draw()


class ScrollableFrame(tk.Frame):
    """Smooth vertically scrollable container with mousewheel support."""

    def __init__(self, parent, bg=UI_BG):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)

        self._win_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.vbar.set)

        self.vbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def _on_canvas_resize(self, event):
        self.canvas.itemconfigure(self._win_id, width=event.width)

    def _bind_wheel(self, _e):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", lambda _e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind_all("<Button-5>", lambda _e: self.canvas.yview_scroll(3, "units"))

    def _unbind_wheel(self, _e):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        delta = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(delta * 3, "units")


# ---------------------------------------------------------------------------
# Multi-Monitor Detection on Windows (EnumDisplayMonitors) & Fallback
# ---------------------------------------------------------------------------
def detect_monitors(root_win=None):
    monitors = []
    if sys.platform == "win32":
        try:
            class RECT(ctypes.Structure):
                _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

            MonitorEnumProc = ctypes.WINFUNCTYPE(
                ctypes.c_int,
                wintypes.HMONITOR,
                wintypes.HDC,
                ctypes.POINTER(RECT),
                wintypes.LPARAM,
            )

            def _cb(hmon, _hdc, lprect, _lparam):
                r = lprect.contents
                idx = len(monitors)
                w = max(320, r.right - r.left)
                h = max(240, r.bottom - r.top)
                monitors.append(
                    {
                        "index": idx,
                        "name": f"Monitor {idx} (DISPLAY{idx + 1} — {w}×{h})",
                        "x": int(r.left),
                        "y": int(r.top),
                        "width": w,
                        "height": h,
                        "scale": 1.0,
                    }
                )
                return 1

            ctypes.windll.user32.EnumDisplayMonitors(0, 0, MonitorEnumProc(_cb), 0)
        except Exception:
            pass

    if not monitors:
        sw = root_win.winfo_screenwidth() if root_win else 1920
        sh = root_win.winfo_screenheight() if root_win else 1080
        monitors.append(
            {
                "index": 0,
                "name": f"Monitor 0 (Primary — {sw}×{sh})",
                "x": 0,
                "y": 0,
                "width": max(320, sw),
                "height": max(240, sh),
                "scale": 1.0,
            }
        )
    return monitors


# ---------------------------------------------------------------------------
# Weather & Village Search Engine (Open-Meteo + met.no + ArcGIS World Geocoder)
# ---------------------------------------------------------------------------
_FORECAST_CACHE = {}


def load_weather_config():
    locations = list(DEFAULT_WEATHER_LOCATIONS)
    active_idx = 0
    units = "metric"
    if os.path.isfile(WEATHER_LOCATIONS_PATH):
        try:
            with open(WEATHER_LOCATIONS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data.get("locations"), list) and data["locations"]:
                locations = data["locations"]
            active_idx = int(data.get("active_index", 0))
            units = data.get("units", "metric")
        except Exception:
            pass
    active_idx = max(0, min(len(locations) - 1, active_idx))
    return locations, active_idx, units


def save_weather_config(locations, active_idx, units="metric"):
    active_idx = max(0, min(len(locations) - 1, active_idx))
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(WEATHER_LOCATIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {"locations": locations, "active_index": active_idx, "units": units},
            f,
            indent=2,
        )
    loc = locations[active_idx]
    weather_inc = (
        "; Auto-generated by Trad Desktop Weather Location Manager\n"
        "[Variables]\n"
        f"WeatherLocationName={loc['name']}\n"
        f"WeatherLat={loc['lat']:.4f}\n"
        f"WeatherLon={loc['lon']:.4f}\n"
        f"WeatherUnits={units}\n"
    )
    for target in (WEATHER_INC_PATH, USER_WEATHER_INC):
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as wf:
                wf.write(weather_inc)
        except Exception:
            pass


def wmo_code_to_description(code):
    mapping = {
        0: "Clear Sky",
        1: "Mainly Clear",
        2: "Partly Cloudy",
        3: "Overcast",
        45: "Foggy",
        48: "Rime Fog",
        51: "Light Drizzle",
        53: "Drizzle",
        55: "Dense Drizzle",
        61: "Slight Rain",
        63: "Moderate Rain",
        65: "Heavy Rain",
        71: "Light Snow",
        73: "Moderate Snow",
        75: "Heavy Snow",
        80: "Rain Showers",
        81: "Heavy Showers",
        82: "Violent Showers",
        95: "Thunderstorm",
        96: "Thunderstorm & Hail",
        99: "Heavy Hailstorm",
    }
    return mapping.get(int(code), "Partly Cloudy")


def deg_to_cardinal(deg):
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return dirs[int(((float(deg) + 11.25) % 360.0) / 22.5) % 16]


def _met_symbol_to_wmo(sym):
    s = str(sym).lower()
    if "thunder" in s:
        return 95
    if "snow" in s or "sleet" in s:
        return 71
    if "heavyrain" in s or "rainshowers" in s:
        return 80
    if "rain" in s:
        return 61
    if "fog" in s:
        return 45
    if "cloud" in s:
        return 2 if "partly" in s else 3
    if "fair" in s:
        return 1
    return 0


def _fetch_forecast_from_met_no(lat, lon, units="metric"):
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={float(lat):.4f}&lon={float(lon):.4f}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "TradDesktop/1.2 (https://github.com/KidDzhasi/Trad-Desktop)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    ts_list = raw.get("properties", {}).get("timeseries", [])
    if not ts_list:
        raise ValueError("Empty met.no timeseries")

    is_imp = str(units).lower() in ("imperial", "fahrenheit", "f")
    c_to_u = (lambda c: c * 9.0 / 5.0 + 32.0) if is_imp else (lambda c: c)
    ms_to_u = (lambda ms: ms * 2.23694) if is_imp else (lambda ms: ms * 3.6)

    def sym_rain_prob(sym):
        s = str(sym).lower()
        if "thunder" in s or "heavyrain" in s:
            return 85
        if "rain" in s or "sleet" in s or "snow" in s:
            return 60
        if "cloudy" in s and "partly" not in s:
            return 20
        if "partly" in s:
            return 10
        return 0

    h_times, h_temps, h_pops, h_codes = [], [], [], []
    by_day = {}
    first_inst = ts_list[0].get("data", {}).get("instant", {}).get("details", {})
    first_next = ts_list[0].get("data", {}).get("next_1_hours") or ts_list[0].get("data", {}).get("next_6_hours") or {}
    first_sym = first_next.get("summary", {}).get("symbol_code", "partlycloudy_day")

    for entry in ts_list:
        iso = entry.get("time", "")
        try:
            dt_utc = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
            dt_loc = dt_utc.astimezone()
        except Exception:
            continue
        inst = entry.get("data", {}).get("instant", {}).get("details", {})
        nxt = entry.get("data", {}).get("next_1_hours") or entry.get("data", {}).get("next_6_hours") or {}
        sym = nxt.get("summary", {}).get("symbol_code", "cloudy")
        temp_v = c_to_u(float(inst.get("air_temperature", 0.0)))
        pop_v = sym_rain_prob(sym)
        wmo_v = _met_symbol_to_wmo(sym)
        h_times.append(dt_loc.strftime("%Y-%m-%dT%H:%M"))
        h_temps.append(round(temp_v, 1))
        h_pops.append(pop_v)
        h_codes.append(wmo_v)
        day_key = dt_loc.strftime("%Y-%m-%d")
        bucket = by_day.setdefault(day_key, {"temps": [], "pops": [], "codes": []})
        bucket["temps"].append(temp_v)
        bucket["pops"].append(pop_v)
        bucket["codes"].append(wmo_v)

    d_times, d_codes, d_max, d_min, d_pop = [], [], [], [], []
    for dk in sorted(by_day.keys())[:7]:
        b = by_day[dk]
        d_times.append(dk)
        d_codes.append(max(b["codes"]))
        d_max.append(round(max(b["temps"]), 1))
        d_min.append(round(min(b["temps"]), 1))
        d_pop.append(max(b["pops"]))

    now_temp = c_to_u(float(first_inst.get("air_temperature", 0.0)))
    return {
        "timezone_abbreviation": "met.no",
        "current": {
            "time": h_times[0] if h_times else "",
            "temperature_2m": round(now_temp, 1),
            "apparent_temperature": round(now_temp, 1),
            "relative_humidity_2m": float(first_inst.get("relative_humidity", 0.0)),
            "precipitation_probability": sym_rain_prob(first_sym),
            "weather_code": _met_symbol_to_wmo(first_sym),
            "wind_speed_10m": round(ms_to_u(float(first_inst.get("wind_speed", 0.0))), 1),
            "wind_direction_10m": float(first_inst.get("wind_from_direction", 0.0)),
            "surface_pressure": float(first_inst.get("air_pressure_at_sea_level", 1013.0)),
        },
        "hourly": {"time": h_times, "temperature_2m": h_temps, "precipitation_probability": h_pops, "weather_code": h_codes},
        "daily": {"time": d_times, "weather_code": d_codes, "temperature_2m_max": d_max, "temperature_2m_min": d_min, "precipitation_probability_max": d_pop},
    }


def fetch_full_weather_forecast(lat, lon, units="metric", force=False):
    cache_key = (round(float(lat), 3), round(float(lon), 3), units)
    now_mono = time.monotonic()
    now_wall = time.time()

    if not force and cache_key in _FORECAST_CACHE:
        ts, cached_data = _FORECAST_CACHE[cache_key]
        if now_mono - ts < 900.0:
            return cached_data

    cache_file = os.path.join(CACHE_DIR, f"forecast_{cache_key[0]:.3f}_{cache_key[1]:.3f}_{units}.json")
    if not force and os.path.isfile(cache_file):
        try:
            if now_wall - os.path.getmtime(cache_file) < 900.0:
                with open(cache_file, "r", encoding="utf-8") as cf:
                    disk_data = json.load(cf)
                if isinstance(disk_data, dict) and "current" in disk_data:
                    _FORECAST_CACHE[cache_key] = (now_mono, disk_data)
                    return disk_data
        except Exception:
            pass

    is_imp = str(units).lower() in ("imperial", "fahrenheit", "f")
    t_unit = "fahrenheit" if is_imp else "celsius"
    w_unit = "mph" if is_imp else "kmh"
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={float(lat):.4f}&longitude={float(lon):.4f}"
        "&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation_probability,"
        "weather_code,surface_pressure,wind_speed_10m,wind_direction_10m"
        "&hourly=temperature_2m,precipitation_probability,weather_code"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
        f"&temperature_unit={t_unit}&wind_speed_unit={w_unit}&timezone=auto&forecast_days=7"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "TradDesktop/1.2", "Accept": "application/json"})
    data = None
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        try:
            data = _fetch_forecast_from_met_no(lat, lon, units=units)
        except Exception:
            if os.path.isfile(cache_file):
                with open(cache_file, "r", encoding="utf-8") as cf:
                    data = json.load(cf)
            else:
                raise

    if isinstance(data, dict) and "current" in data:
        _FORECAST_CACHE[cache_key] = (now_mono, data)
        try:
            with open(cache_file, "w", encoding="utf-8") as cf:
                json.dump(data, cf)
        except Exception:
            pass
    return data


def search_village_or_city(query):
    q = query.strip()
    if not q:
        return []

    coord_m = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$", q)
    if coord_m:
        lat, lon = float(coord_m.group(1)), float(coord_m.group(2))
        return [{"name": f"Custom Coordinates ({lat:.4f}, {lon:.4f})", "lat": lat, "lon": lon, "source": "Coordinates"}]

    clean_q = re.sub(r"\b(village|location|rural|township|ward)\b", "", q, flags=re.IGNORECASE).strip(" ,") or q
    results = []
    seen = set()

    def _add(name, lat, lon, src):
        key = (round(lat, 2), round(lon, 2))
        if key not in seen:
            seen.add(key)
            results.append({"name": name, "lat": lat, "lon": lon, "source": src})

    def _query_arcgis():
        out = []
        url = (
            "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"
            f"?SingleLine={urllib.parse.quote(clean_q)}&maxLocations=8&outFields=LongLabel,Place_addr,Type&f=json"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "TradDesktop/1.2"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for c in data.get("candidates", []):
            loc = c.get("location", {})
            lat, lon = loc.get("y"), loc.get("x")
            if lat is None or lon is None:
                continue
            attrs = c.get("attributes", {})
            label = attrs.get("LongLabel") or c.get("address") or clean_q
            parts = [p.strip() for p in label.split(",") if p.strip() and not p.strip().isdigit()]
            short_name = ", ".join(dict.fromkeys(parts[:3]))
            out.append((short_name, float(lat), float(lon), "ArcGIS World Geocoder"))
        return out

    def _query_open_meteo():
        out = []
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(clean_q)}&count=8&language=en&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "TradDesktop/1.2"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for r in data.get("results", []):
            parts = [r.get("name", ""), r.get("admin1", ""), r.get("country", "")]
            label = ", ".join(p for p in parts if p)
            out.append((label, float(r["latitude"]), float(r["longitude"]), "Open-Meteo"))
        return out

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        f_arc = pool.submit(_query_arcgis)
        f_om = pool.submit(_query_open_meteo)
        for fut in (f_arc, f_om):
            try:
                for name, lat, lon, src in fut.result(timeout=7):
                    _add(name, lat, lon, src)
            except Exception:
                pass

    return results[:12]


# ---------------------------------------------------------------------------
# System Telemetry & Media Backend for Windows
# ---------------------------------------------------------------------------
class SystemTelemetryBackend:
    def __init__(self):
        self.cpu_percent = 0.0
        self.ram_percent = 0.0
        self.ram_used_bytes = 0
        self.ram_total_bytes = 8 * 1024**3
        self.swap_percent = 0.0
        self.swap_used_bytes = 0
        self.disk_percent = 0.0
        self.disk_used_bytes = 0
        self.disk_free_bytes = 0
        self.net_in_bps = 0.0
        self.net_out_bps = 0.0
        self._last_net_time = time.monotonic()
        self._last_rx = 0
        self._last_tx = 0
        self.fft_bands = [0.05] * 20
        self._fft_phase = 0.0
        self.media_playing = False
        self.media_title = "No Media Playing"
        self.media_artist = "Start Spotify, Browser, or Media Player"
        self.weather_data = {
            "Temp": "19°C",
            "TempNum": 19.0,
            "Condition": "Partly Cloudy",
            "Humidity": "62",
            "RainProb": "10",
            "WindSpeed": "12 km/h",
            "WindDir": "NE",
            "High": "24°",
            "Low": "13°",
            "FeelsLike": "18°",
            "Location": "Johannesburg, South Africa",
            "Updated": "Just now",
        }
        self._last_weather_fetch = 0.0
        self._weather_lock = threading.Lock()
        self.update_telemetry()

    def refresh_weather_async(self, force=False):
        now = time.monotonic()
        if not force and now - self._last_weather_fetch < 300.0:
            return
        self._last_weather_fetch = now

        def _worker():
            try:
                locs, idx, units = load_weather_config()
                loc = locs[idx]
                data = fetch_full_weather_forecast(loc["lat"], loc["lon"], units=units, force=force)
                cur = data.get("current", {})
                daily = data.get("daily", {})
                is_imp = units == "imperial"
                t_sym = "°F" if is_imp else "°C"
                w_sym = "mph" if is_imp else "km/h"
                temp_val = float(cur.get("temperature_2m", 19.0))
                hi_list = daily.get("temperature_2m_max", [temp_val + 4])
                lo_list = daily.get("temperature_2m_min", [temp_val - 4])
                with self._weather_lock:
                    self.weather_data = {
                        "Temp": f"{round(temp_val)}{t_sym}",
                        "TempNum": temp_val,
                        "Condition": wmo_code_to_description(cur.get("weather_code", 2)),
                        "Humidity": str(round(float(cur.get("relative_humidity_2m", 60)))),
                        "RainProb": str(round(float(cur.get("precipitation_probability", 0)))),
                        "WindSpeed": f"{round(float(cur.get('wind_speed_10m', 10)))} {w_sym}",
                        "WindDir": deg_to_cardinal(cur.get("wind_direction_10m", 45)),
                        "High": f"{round(float(hi_list[0]))}°" if hi_list else "--°",
                        "Low": f"{round(float(lo_list[0]))}°" if lo_list else "--°",
                        "FeelsLike": f"{round(float(cur.get('apparent_temperature', temp_val)))}°",
                        "Location": loc["name"],
                        "Updated": datetime.datetime.now().strftime("Updated %H:%M"),
                    }
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def update_telemetry(self):
        self.refresh_weather_async(force=False)
        if psutil is not None:
            try:
                self.cpu_percent = psutil.cpu_percent(interval=None)
                vm = psutil.virtual_memory()
                self.ram_percent = vm.percent
                self.ram_used_bytes = vm.used
                self.ram_total_bytes = vm.total
                sm = psutil.swap_memory()
                self.swap_percent = sm.percent
                self.swap_used_bytes = sm.used
                root_path = "C:\\" if sys.platform == "win32" else "/"
                du = psutil.disk_usage(root_path)
                self.disk_percent = du.percent
                self.disk_used_bytes = du.used
                self.disk_free_bytes = du.free
                nio = psutil.net_io_counters()
                now = time.monotonic()
                dt = max(0.05, now - self._last_net_time)
                if self._last_rx > 0:
                    self.net_in_bps = max(0.0, (nio.bytes_recv - self._last_rx) / dt)
                    self.net_out_bps = max(0.0, (nio.bytes_sent - self._last_tx) / dt)
                self._last_rx = nio.bytes_recv
                self._last_tx = nio.bytes_sent
                self._last_net_time = now
            except Exception:
                pass
        elif sys.platform == "win32":
            try:
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                mem = MEMORYSTATUSEX()
                mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
                self.ram_percent = float(mem.dwMemoryLoad)
                self.ram_total_bytes = mem.ullTotalPhys
                self.ram_used_bytes = mem.ullTotalPhys - mem.ullAvailPhys

                free_b = ctypes.c_ulonglong(0)
                total_b = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p("C:\\"),
                    ctypes.byref(free_b),
                    ctypes.byref(total_b),
                    None,
                )
                if total_b.value > 0:
                    self.disk_free_bytes = free_b.value
                    self.disk_used_bytes = total_b.value - free_b.value
                    self.disk_percent = (self.disk_used_bytes / total_b.value) * 100.0
            except Exception:
                pass

        self._fft_phase += 0.35
        for i in range(20):
            if self.media_playing:
                val = 0.25 + 0.35 * abs(math.sin(self._fft_phase + i * 0.45)) + 0.25 * abs(math.cos(self._fft_phase * 1.3 - i * 0.3))
            else:
                val = 0.04 + 0.03 * abs(math.sin(self._fft_phase * 0.5 + i * 0.4))
            self.fft_bands[i] = max(0.03, min(0.95, val))

    def send_media_command(self, cmd):
        c = cmd.strip().lower()
        if sys.platform == "win32":
            vk = 0xB3
            if "next" in c:
                vk = 0xB0
            elif "prev" in c:
                vk = 0xB1
            else:
                self.media_playing = not self.media_playing
            try:
                ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
                ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
            except Exception:
                pass
        else:
            if "playpause" in c:
                self.media_playing = not self.media_playing


# ---------------------------------------------------------------------------
# Theme, Config & Skin Discovery
# ---------------------------------------------------------------------------
def write_basic_theme(theme, shape=None, design=None):
    if shape is None:
        shape = BASIC_WIDGET_SHAPES[0]
    if design is None:
        design = BASIC_WIDGET_DESIGNS[0]

    radius = theme["corner_radius"] if shape["radius"] is None else shape["radius"]
    if shape.get("borderless", False):
        bg_fill = "Fill Color 0,0,0,0"
        border_stroke = "StrokeWidth 0 | Stroke Color 0,0,0,0"
    else:
        bg_fill = theme["bg_fill"]
        border_stroke = theme["border_stroke"]

    content = (
        "; Auto-generated by Trad Desktop Theme, Shape & Design Studio\n"
        f"; Theme: {theme['name']}\n"
        f"; Shape: {shape['name']}\n"
        f"; Design: {design['name']}\n"
        "[Variables]\n"
        f"ThemeName={theme['name']}\n"
        f"WidgetShape={shape['id']}\n"
        f"WidgetDesign={design['id']}\n"
        f"CornerRadius={radius}\n"
        f"BgFill={bg_fill}\n"
        f"BorderStroke={border_stroke}\n"
        f"AccentColor={theme['accent']}\n"
        f"TextColor={theme['text']}\n"
    )
    for target in (THEME_INC_PATH, USER_THEME_INC):
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            pass


def read_current_basic_style():
    theme_idx, shape_idx, design_idx = 0, 0, 0
    src = USER_THEME_INC if os.path.isfile(USER_THEME_INC) else THEME_INC_PATH
    if os.path.isfile(src):
        try:
            with open(src, "r", encoding="utf-8") as f:
                txt = f.read()
            for i, t in enumerate(BASIC_WIDGET_THEMES):
                if f"ThemeName={t['name']}" in txt:
                    theme_idx = i
                    break
            for i, s in enumerate(BASIC_WIDGET_SHAPES):
                if f"WidgetShape={s['id']}" in txt:
                    shape_idx = i
                    break
            for i, d in enumerate(BASIC_WIDGET_DESIGNS):
                if f"WidgetDesign={d['id']}" in txt:
                    design_idx = i
                    break
        except Exception:
            pass
    return theme_idx, shape_idx, design_idx


def compute_autofit_scale(skin_info, mon_w, mon_h):
    raw_w = max(1, skin_info["est_w"])
    raw_h = max(1, skin_info["est_h"])
    if raw_w >= 1000 or raw_h >= 650:
        return round(min(mon_w / raw_w, mon_h / raw_h), 2)
    scale = max(0.6, min(2.5, mon_h / 768.0))
    if raw_w * scale > mon_w:
        scale = mon_w / raw_w
    return round(scale, 2)


def estimate_skin_size(ini_path):
    info = {"width": 260, "height": 140, "anchor_x": "left", "anchor_y": "top", "window_x": None, "window_y": None}
    if not os.path.isfile(ini_path):
        return info
    max_x, max_y, explicit_w, explicit_h = 240, 100, 0, 0
    try:
        with open(ini_path, "r", encoding="utf-8", errors="ignore") as f:
            section = ""
            cur_x = cur_y = cur_w = cur_h = 0.0
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith(";"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    max_x = max(max_x, cur_x + max(cur_w, 40))
                    max_y = max(max_y, cur_y + max(cur_h, 24))
                    section = line[1:-1].strip().lower()
                    cur_x = cur_y = cur_w = cur_h = 0.0
                    continue
                if "=" not in line:
                    continue
                k, v = [p.strip() for p in line.split("=", 1)]
                kl = k.lower()
                if section == "rainmeter":
                    if kl == "anchorx" and v.lower() in ("left", "center", "right"):
                        info["anchor_x"] = v.lower()
                    elif kl == "anchory" and v.lower() in ("top", "center", "bottom"):
                        info["anchor_y"] = v.lower()
                    elif kl == "windowx":
                        try:
                            info["window_x"] = int(float(v))
                        except ValueError:
                            pass
                    elif kl == "windowy":
                        try:
                            info["window_y"] = int(float(v))
                        except ValueError:
                            pass
                    elif kl == "skinwidth":
                        try:
                            explicit_w = max(64, int(float(v)))
                        except ValueError:
                            pass
                    elif kl == "skinheight":
                        try:
                            explicit_h = max(64, int(float(v)))
                        except ValueError:
                            pass
                else:
                    try:
                        if kl == "x" and not v.lower().endswith("r"):
                            cur_x = float(v)
                        elif kl == "y" and not v.lower().endswith("r"):
                            cur_y = float(v)
                        elif kl == "w":
                            cur_w = float(v)
                        elif kl == "h":
                            cur_h = float(v)
                        elif kl == "shape" and "rectangle" in v.lower():
                            parts = v.split("|")[0].split(",")
                            if len(parts) >= 4:
                                cur_w = max(cur_w, float(parts[2].strip()))
                                cur_h = max(cur_h, float(parts[3].strip()))
                    except ValueError:
                        pass
            max_x = max(max_x, cur_x + max(cur_w, 40))
            max_y = max(max_y, cur_y + max(cur_h, 24))
        info["width"] = explicit_w if explicit_w > 0 else int(min(1920, max(120, max_x)))
        info["height"] = explicit_h if explicit_h > 0 else int(min(1080, max(80, max_y)))
    except Exception:
        pass
    return info


WIDGET_DESCRIPTIONS = {
    "AudioHorizon": "Floating Minimalist 20-Band Spectrum + Glowing Horizon Axis Line (30 FPS)",
    "AudioVisualizer": "20-Band Real-Time Spectrum Analyzer Card • Live Audio FFT (30 FPS)",
    "MusicBanner": "Banner Music Player • Cover Art + Track Info + Media Controls + Progress Bar",
    "MusicCompact": "Compact Glass Music Pill • Track Info + Play/Pause & Skip Controls",
    "MusicMinimal": "Minimalist Track Display • Clean Title, Artist & Playback Transport",
    "BasicClock": "Digital / Radial Wall Clock • Live Time & Seconds",
    "BasicDate": "Day & Calendar Card • Weekday, Date & Year Display",
    "BasicWeather": "Live Weather Card • Open-Meteo & met.no Forecast (Click to Expand)",
    "BasicCpu": "Processor Telemetry • Real-Time CPU Load Gauge",
    "BasicRamSwap": "Memory Telemetry • RAM & Pagefile Usage Monitor",
    "BasicNet": "Network Activity • Live Download / Upload Speedometer",
    "BasicDisks": "Disk I/O Telemetry • Storage Read / Write Activity",
    "BasicStorage": "Drive Capacity • Used & Free Storage Gauge",
}


def discover_all_skins():
    items = []
    seen_abs = set()
    for suites_base in dict.fromkeys([SYSTEM_SUITES_DIR, SUITES_DIR]):
        if not os.path.isdir(suites_base):
            continue
        for folder in sorted(os.listdir(suites_base)):
            folder_path = os.path.join(suites_base, folder)
            if not os.path.isdir(folder_path) or os.path.isfile(os.path.join(folder_path, "suite.json")):
                continue
            for root, _dirs, files in os.walk(folder_path):
                for file in sorted(files):
                    if file.lower().endswith(".ini"):
                        abs_p = os.path.abspath(os.path.join(root, file))
                        if abs_p in seen_abs:
                            continue
                        seen_abs.add(abs_p)
                        rel_key = f"suites/{folder}/{file}"
                        meta = estimate_skin_size(abs_p)
                        items.append(
                            {
                                "key": rel_key,
                                "title": folder if file.lower() == f"{folder.lower()}.ini" else f"{folder} / {file[:-4]}",
                                "subtitle": rel_key,
                                "abs_path": abs_p,
                                "is_suite": True,
                                "is_basic": False,
                                "source": "Built-in Suite",
                                "est_w": meta["width"],
                                "est_h": meta["height"],
                                "default_anchor_x": meta["anchor_x"],
                                "default_anchor_y": meta["anchor_y"],
                                "default_x": meta["window_x"],
                                "default_y": meta["window_y"],
                            }
                        )

    if os.path.isdir(WIDGETS_DIR):
        for folder in sorted(os.listdir(WIDGETS_DIR)):
            folder_path = os.path.join(WIDGETS_DIR, folder)
            if not os.path.isdir(folder_path):
                continue
            for root, _dirs, files in os.walk(folder_path):
                for file in sorted(files):
                    if file.lower().endswith(".ini"):
                        abs_p = os.path.abspath(os.path.join(root, file))
                        if abs_p in seen_abs:
                            continue
                        seen_abs.add(abs_p)
                        rel_key = f"widgets/{folder}/{file}"
                        meta = estimate_skin_size(abs_p)
                        title = folder if file.lower() == f"{folder.lower()}.ini" else f"{folder} / {file[:-4]}"
                        items.append(
                            {
                                "key": rel_key,
                                "title": title,
                                "subtitle": f"Anchored ({meta['anchor_x'].capitalize()}-{meta['anchor_y'].capitalize()}) • {meta['width']}×{meta['height']}",
                                "desc": WIDGET_DESCRIPTIONS.get(folder, f"Anchored ({meta['anchor_x'].capitalize()}-{meta['anchor_y'].capitalize()}) • {meta['width']}×{meta['height']}"),
                                "abs_path": abs_p,
                                "is_suite": False,
                                "is_basic": True,
                                "source": "Basic Widget",
                                "est_w": meta["width"],
                                "est_h": meta["height"],
                                "default_anchor_x": meta["anchor_x"],
                                "default_anchor_y": meta["anchor_y"],
                                "default_x": meta["window_x"],
                                "default_y": meta["window_y"],
                            }
                        )

    os.makedirs(USER_SKINS_DIR, exist_ok=True)
    for root, _dirs, files in os.walk(USER_SKINS_DIR):
        if "@resources" in root.lower():
            continue
        for file in sorted(files):
            if file.lower().endswith(".ini") and file.lower() != "rmskin.ini":
                abs_p = os.path.abspath(os.path.join(root, file))
                if abs_p in seen_abs:
                    continue
                seen_abs.add(abs_p)
                rel_from_skins = os.path.relpath(abs_p, USER_SKINS_DIR).replace("\\", "/")
                meta = estimate_skin_size(abs_p)
                items.append(
                    {
                        "key": abs_p,
                        "title": os.path.splitext(rel_from_skins)[0].replace("/", " / "),
                        "subtitle": rel_from_skins,
                        "desc": rel_from_skins,
                        "abs_path": abs_p,
                        "is_suite": False,
                        "is_basic": False,
                        "source": "Custom Widget",
                        "est_w": meta["width"],
                        "est_h": meta["height"],
                        "default_anchor_x": meta["anchor_x"],
                        "default_anchor_y": meta["anchor_y"],
                        "default_x": meta["window_x"],
                        "default_y": meta["window_y"],
                    }
                )
    return items


def discover_custom_suites():
    custom_suites = []
    for base in dict.fromkeys([SUITES_DIR, SYSTEM_SUITES_DIR]):
        if not os.path.isdir(base):
            continue
        for folder in sorted(os.listdir(base)):
            manifest_path = os.path.join(base, folder, "suite.json")
            if os.path.isfile(manifest_path):
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    cid = f"custom_suite::{folder}"
                    if not any(c["id"] == cid for c in custom_suites):
                        custom_suites.append(
                            {
                                "id": cid,
                                "folder": folder,
                                "title": data.get("name", folder),
                                "manifest_path": manifest_path,
                                "widgets": data.get("widgets", []),
                            }
                        )
                except Exception:
                    continue
    return custom_suites


def load_global_config(skins):
    state = {}
    for s in skins:
        has_def_xy = s.get("default_x") is not None and s.get("default_y") is not None
        state[s["key"]] = {
            "active": False,
            "monitor": 0,
            "monitors": [],
            "anchor_x": s["default_anchor_x"],
            "anchor_y": s["default_anchor_y"],
            "use_custom_pos": has_def_xy,
            "x": s["default_x"] if has_def_xy else 0,
            "y": s["default_y"] if has_def_xy else 0,
            "ref_w": 1366,
            "ref_h": 768,
            "auto_fit": True,
            "scale": 1.0,
        }
    if not os.path.isfile(GLOBAL_CONFIG):
        for s in skins:
            if "TradSunset" in s["key"]:
                state[s["key"]]["active"] = True
                state[s["key"]]["monitors"] = [0]
                break
        return state

    cp = configparser.ConfigParser(interpolation=None, strict=False)
    cp.optionxform = str
    try:
        with open(GLOBAL_CONFIG, "r", encoding="utf-8", errors="ignore") as f:
            cp.read_file(f)
        for sec in cp.sections():
            norm_sec = sec.replace("\\", "/")
            tag_mon = None
            if "@" in norm_sec:
                r_at = norm_sec.rfind("@")
                suffix = norm_sec[r_at + 1 :]
                if suffix.isdigit():
                    norm_sec = norm_sec[:r_at]
                    tag_mon = int(suffix)
            matched_key = next(
                (s["key"] for s in skins if norm_sec == s["key"] or s["abs_path"].replace("\\", "/").endswith(norm_sec)),
                None,
            )
            if not matched_key:
                continue
            st = state[matched_key]
            sec_map = {k.lower(): v.strip() for k, v in cp.items(sec)}
            is_act = sec_map.get("active", "0") not in ("0", "false", "")
            mon_val = tag_mon if tag_mon is not None else 0
            if "monitor" in sec_map:
                try:
                    mon_val = int(float(sec_map["monitor"]))
                except ValueError:
                    pass
            if is_act:
                st["active"] = True
                if mon_val >= 0 and mon_val not in st["monitors"]:
                    st["monitors"].append(mon_val)
                    st["monitors"].sort()
                if len(st["monitors"]) > 1:
                    st["monitor"] = -1
                elif st["monitors"]:
                    st["monitor"] = st["monitors"][0]
                else:
                    st["monitor"] = max(0, mon_val)
            elif not st["active"]:
                st["monitor"] = max(0, mon_val)
            if "anchorx" in sec_map and sec_map["anchorx"].lower() in ("left", "center", "right"):
                st["anchor_x"] = sec_map["anchorx"].lower()
            if "anchory" in sec_map and sec_map["anchory"].lower() in ("top", "center", "bottom"):
                st["anchor_y"] = sec_map["anchory"].lower()
            if "scale" in sec_map:
                try:
                    st["scale"] = max(0.25, min(3.0, float(sec_map["scale"])))
                except ValueError:
                    pass
            if "autofit" in sec_map:
                st["auto_fit"] = sec_map["autofit"].lower() in ("1", "true", "yes")
            elif "scale" in sec_map:
                st["auto_fit"] = False
            if "refwidth" in sec_map:
                try:
                    st["ref_w"] = max(320, int(float(sec_map["refwidth"])))
                except ValueError:
                    pass
            if "refheight" in sec_map:
                try:
                    st["ref_h"] = max(240, int(float(sec_map["refheight"])))
                except ValueError:
                    pass
            if "windowx" in sec_map or "windowy" in sec_map:
                try:
                    st["x"] = int(float(sec_map.get("windowx", "0")))
                    st["y"] = int(float(sec_map.get("windowy", "0")))
                    st["use_custom_pos"] = True
                except ValueError:
                    pass
    except Exception:
        pass
    return state


def get_active_monitors_for_skin(st, num_monitors=1):
    if not st.get("active", False):
        return []
    if st.get("monitor", 0) == -1:
        return list(range(max(1, num_monitors)))
    mons = [m for m in st.get("monitors", []) if 0 <= m < max(1, num_monitors)]
    if mons:
        return sorted(list(dict.fromkeys(mons)))
    m_single = max(0, min(max(1, num_monitors) - 1, int(st.get("monitor", 0))))
    return [m_single]


def save_global_config(skins, state, num_monitors=1):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    lines = ["; Rainmeter Native Global Configuration\n"]
    for s in skins:
        key = s["key"]
        st = state.get(key)
        if not st:
            continue
        act_mons = get_active_monitors_for_skin(st, num_monitors)
        if not act_mons:
            lines.append(f"[{key}]\n")
            lines.append("Active=0\n")
            lines.append(f"Monitor={max(0, st.get('monitor', 0))}\n")
            lines.append(f"AnchorX={st['anchor_x'].capitalize()}\n")
            lines.append(f"AnchorY={st['anchor_y'].capitalize()}\n")
            lines.append(f"AutoFit={1 if st['auto_fit'] else 0}\n")
            if not st["auto_fit"]:
                lines.append(f"Scale={st['scale']:.2f}\n")
            if st["use_custom_pos"]:
                lines.append(f"RefWidth={int(st.get('ref_w', 1366))}\n")
                lines.append(f"RefHeight={int(st.get('ref_h', 768))}\n")
                lines.append(f"WindowX={int(st['x'])}\n")
                lines.append(f"WindowY={int(st['y'])}\n")
            lines.append("\n")
            continue
        for m_idx in act_mons:
            sec_name = f"{key}@{m_idx}" if len(act_mons) > 1 or m_idx > 0 else key
            lines.append(f"[{sec_name}]\n")
            lines.append("Active=1\n")
            lines.append(f"Monitor={m_idx}\n")
            lines.append(f"AnchorX={st['anchor_x'].capitalize()}\n")
            lines.append(f"AnchorY={st['anchor_y'].capitalize()}\n")
            lines.append(f"AutoFit={1 if st['auto_fit'] else 0}\n")
            if not st["auto_fit"]:
                lines.append(f"Scale={st['scale']:.2f}\n")
            if st["use_custom_pos"]:
                lines.append(f"RefWidth={int(st.get('ref_w', 1366))}\n")
                lines.append(f"RefHeight={int(st.get('ref_h', 768))}\n")
                lines.append(f"WindowX={int(st['x'])}\n")
                lines.append(f"WindowY={int(st['y'])}\n")
            lines.append("\n")
    with open(GLOBAL_CONFIG, "w", encoding="utf-8") as f:
        f.writelines(lines)


# ---------------------------------------------------------------------------
# Pinned Desktop Widget Renderer Window (Win32 HWND_BOTTOM Desktop Overlay)
# ---------------------------------------------------------------------------
class DesktopWidgetWindow:
    def __init__(self, master, skin_info, skin_state, monitors, telemetry, on_open_weather, mon_idx=None):
        self.master = master
        self.skin_info = skin_info
        self.state = skin_state
        self.telemetry = telemetry
        self.on_open_weather = on_open_weather

        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)

        if mon_idx is None:
            mon_idx = max(0, skin_state.get("monitor", 0))
        mon_idx = max(0, min(mon_idx, len(monitors) - 1))
        mon = monitors[mon_idx]
        mx, my, mw, mh = mon["x"], mon["y"], mon["width"], mon["height"]

        eff_scale = compute_autofit_scale(skin_info, mw, mh) if skin_state.get("auto_fit", False) else skin_state.get("scale", 1.0)
        w = max(120, min(mw, int(skin_info["est_w"] * eff_scale)))
        h = max(70, min(mh, int(skin_info["est_h"] * eff_scale)))
        if skin_info["is_suite"]:
            w = min(mw, max(480, w))
            h = min(mh, max(320, h))

        if skin_state.get("use_custom_pos"):
            raw_x = float(skin_state.get("x", 0))
            raw_y = float(skin_state.get("y", 0))
            if skin_state.get("auto_fit", False):
                ref_w = max(320, int(skin_state.get("ref_w", 1366)))
                ref_h = max(240, int(skin_state.get("ref_h", 768)))
                if mw != ref_w or mh != ref_h:
                    raw_x = raw_x * (mw / float(ref_w))
                    raw_y = raw_y * (mh / float(ref_h))
            x = mx + max(0, min(mw - w, int(round(raw_x))))
            y = my + max(0, min(mh - h, int(round(raw_y))))
        else:
            ax = skin_state.get("anchor_x", "center")
            ay = skin_state.get("anchor_y", "center")
            x = mx + ((mw - w) // 2 if ax == "center" else (mw - w - 24 if ax == "right" else 24))
            y = my + ((mh - h) // 2 if ay == "center" else (mh - h - 48 if ay == "bottom" else 36))

        self.pinned_x = x
        self.pinned_y = y
        self.width = w
        self.height = h
        self.win.geometry(f"{w}x{h}+{x}+{y}")

        self.transparent_key = "#010203"
        self.win.configure(bg=self.transparent_key)
        if sys.platform == "win32":
            try:
                self.win.wm_attributes("-transparentcolor", self.transparent_key)
            except Exception:
                pass

        self.canvas = tk.Canvas(
            self.win,
            width=w,
            height=h,
            bg=self.transparent_key,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self._on_click)

        self._pin_to_desktop_bottom()
        self.redraw()

    def _pin_to_desktop_bottom(self):
        if sys.platform == "win32":
            try:
                self.win.update_idletasks()
                hwnd = ctypes.windll.user32.GetParent(self.win.winfo_id()) or self.win.winfo_id()
                GWL_EXSTYLE = -20
                WS_EX_TOOLWINDOW = 0x00000080
                WS_EX_NOACTIVATE = 0x08000000
                style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
                ctypes.windll.user32.SetWindowPos(
                    hwnd, 1, self.pinned_x, self.pinned_y, self.width, self.height, 0x0010
                )
            except Exception:
                pass
        else:
            try:
                self.win.lower()
            except Exception:
                pass

    def _on_click(self, event):
        title = self.skin_info["title"].lower()
        if "weather" in title or (self.skin_info["is_suite"] and event.x > self.width * 0.6):
            self.on_open_weather()
            return
        if "music" in title or self.skin_info["is_suite"]:
            rel_x = event.x / max(1, self.width)
            if rel_x < 0.42:
                self.telemetry.send_media_command("Previous")
            elif rel_x > 0.58:
                self.telemetry.send_media_command("Next")
            else:
                self.telemetry.send_media_command("PlayPause")
            self.redraw()

    def redraw(self):
        if not self.win.winfo_exists():
            return
        self._pin_to_desktop_bottom()
        c = self.canvas
        c.delete("all")

        t_idx, s_idx, d_idx = read_current_basic_style()
        theme = BASIC_WIDGET_THEMES[t_idx]
        shape = BASIC_WIDGET_SHAPES[s_idx]
        design = BASIC_WIDGET_DESIGNS[d_idx]

        bg_hex = theme["bg_hex"]
        bd_hex = theme["border_hex"]
        ac_hex = theme["accent_hex"]
        now = datetime.datetime.now()
        w_data = self.telemetry.weather_data
        title = self.skin_info["title"]

        if self.skin_info["is_suite"]:
            cx, cy = self.width // 2, self.height // 2
            day_spaced = "  ".join(list(now.strftime("%A").upper()))
            c.create_text(cx, cy - 35, text=day_spaced, fill="#FFFFFF", font=("Segoe UI", 26, "bold"))
            c.create_text(cx, cy + 14, text=now.strftime("%d  %b  %Y").upper(), fill="#E2E8F0", font=("Segoe UI", 12, "bold"))
            c.create_text(cx, cy + 40, text=now.strftime("-  %I : %M  %p  -"), fill=ac_hex, font=("Segoe UI", 12, "bold"))

            for label, pct, gx in [("DISK", self.telemetry.disk_percent, self.width - 185), ("CPU", self.telemetry.cpu_percent, self.width - 80)]:
                gy = 62
                c.create_oval(gx - 34, gy - 34, gx + 34, gy + 34, outline="#2A324B", width=6)
                extent = -max(5.0, min(359.0, (pct / 100.0) * 360.0))
                c.create_arc(gx - 34, gy - 34, gx + 34, gy + 34, start=90, extent=extent, style="arc", outline="#FFB703" if "Sunset" in title else ac_hex, width=6)
                c.create_text(gx, gy - 6, text=f"{pct:.1f}%", fill="#FFFFFF", font=("Segoe UI", 10, "bold"))
                c.create_text(gx, gy + 12, text=label, fill="#94A3B8", font=("Segoe UI", 8, "bold"))

            mx, my = self.width - 230, 150
            c.create_text(mx, my, anchor="w", text=self.telemetry.media_title, fill="#FFFFFF", font=("Segoe UI", 10, "bold"))
            c.create_text(mx, my + 18, anchor="w", text=self.telemetry.media_artist, fill="#94A3B8", font=("Segoe UI", 8))
            play_sym = "⏸" if self.telemetry.media_playing else "▶"
            c.create_text(self.width - 55, my + 8, text=f"⏮   {play_sym}   ⏭", fill="#FFB703", font=("Segoe UI", 12, "bold"))

            wx, wy = self.width - 230, 225
            c.create_text(wx, wy, anchor="w", text=w_data["Location"], fill="#FFB703", font=("Segoe UI", 10, "bold"))
            c.create_text(wx, wy + 18, anchor="w", text=f"Currently - {w_data['Condition']}", fill="#FFFFFF", font=("Segoe UI", 9))
            c.create_text(wx, wy + 38, anchor="w", text=f"H {w_data['High']}  L {w_data['Low']}  Feels {w_data['FeelsLike']}", fill="#94A3B8", font=("Segoe UI", 8))
            c.create_text(self.width - 30, wy + 28, anchor="e", text=w_data["Temp"], fill="#FFFFFF", font=("Segoe UI", 22, "bold"))
            c.create_text(wx, wy + 60, anchor="w", text=f"Humidity: {w_data['Humidity']}%  •  Rain: {w_data['RainProb']}%", fill="#94A3B8", font=("Segoe UI", 8))
            c.create_text(wx, wy + 76, anchor="w", text=f"Wind: {w_data['WindSpeed']} - {w_data['WindDir']}  ({w_data['Updated']})", fill="#94A3B8", font=("Segoe UI", 8))

            vx, vy = self.width - 240, self.height - 20
            for b_idx, amp in enumerate(self.telemetry.fft_bands):
                bh = max(4, int(amp * 70))
                bx = vx + b_idx * 11
                c.create_rectangle(bx, vy - bh, bx + 8, vy, fill="#FFB703" if "Sunset" in title else ac_hex, outline="")
            return

        if not shape.get("borderless", False) and theme["name"] != "Pure Transparent":
            rad = theme["corner_radius"] if shape["radius"] is None else shape["radius"]
            draw_round_rect(c, 3, 3, self.width - 3, self.height - 3, rad, fill=bg_hex, outline=bd_hex, width=2)

        if "Clock" in title:
            c.create_text(self.width // 2, self.height // 2 - 8, text=now.strftime("%H : %M"), fill="#FFFFFF", font=("Segoe UI", 24, "bold"))
            c.create_text(self.width // 2, self.height // 2 + 22, text=now.strftime("%S sec"), fill=ac_hex, font=("Segoe UI", 10, "bold"))
        elif "Date" in title:
            c.create_text(self.width // 2, self.height // 2 - 12, text=now.strftime("%A").upper(), fill=ac_hex, font=("Segoe UI", 13, "bold"))
            c.create_text(self.width // 2, self.height // 2 + 14, text=now.strftime("%d %B %Y"), fill="#FFFFFF", font=("Segoe UI", 11))
        elif "Weather" in title:
            c.create_text(14, 20, anchor="w", text=w_data["Location"][:24], fill=ac_hex, font=("Segoe UI", 10, "bold"))
            c.create_text(14, 42, anchor="w", text=w_data["Condition"], fill="#FFFFFF", font=("Segoe UI", 10))
            c.create_text(self.width - 14, 34, anchor="e", text=w_data["Temp"], fill="#FFFFFF", font=("Segoe UI", 20, "bold"))
            c.create_text(14, 68, anchor="w", text=f"H {w_data['High']} L {w_data['Low']} • Rain {w_data['RainProb']}% • Hum {w_data['Humidity']}%", fill="#CBD5E1", font=("Segoe UI", 8))
            c.create_text(14, 86, anchor="w", text=f"Wind {w_data['WindSpeed']} ({w_data['WindDir']}) • Click for 7-Day Forecast", fill="#94A3B8", font=("Segoe UI", 8))
        elif "Cpu" in title:
            self._draw_metric_card(c, "CPU LOAD", self.telemetry.cpu_percent, f"{self.telemetry.cpu_percent:.1f}%", ac_hex, design["id"])
        elif "Ram" in title:
            used_gb = self.telemetry.ram_used_bytes / (1024**3)
            self._draw_metric_card(c, "RAM & SWAP", self.telemetry.ram_percent, f"{used_gb:.1f} GB ({self.telemetry.ram_percent:.0f}%)", ac_hex, design["id"])
        elif "Disk" in title or "Storage" in title:
            free_gb = self.telemetry.disk_free_bytes / (1024**3)
            self._draw_metric_card(c, "STORAGE (C:)", self.telemetry.disk_percent, f"{free_gb:.1f} GB Free ({self.telemetry.disk_percent:.0f}%)", ac_hex, design["id"])
        elif "Net" in title:
            in_kb = self.telemetry.net_in_bps / 1024.0
            out_kb = self.telemetry.net_out_bps / 1024.0
            c.create_text(14, 22, anchor="w", text="NETWORK I/O", fill=ac_hex, font=("Segoe UI", 10, "bold"))
            c.create_text(14, 48, anchor="w", text=f"↓ Down: {in_kb:.1f} KB/s", fill="#FFFFFF", font=("Segoe UI", 10))
            c.create_text(14, 70, anchor="w", text=f"↑ Up:   {out_kb:.1f} KB/s", fill="#CBD5E1", font=("Segoe UI", 10))
        elif "Music" in title:
            c.create_text(14, 22, anchor="w", text=self.telemetry.media_title[:26], fill="#FFFFFF", font=("Segoe UI", 10, "bold"))
            c.create_text(14, 42, anchor="w", text=self.telemetry.media_artist[:32], fill=ac_hex, font=("Segoe UI", 8))
            play_sym = "⏸ Pause" if self.telemetry.media_playing else "▶ Play"
            c.create_text(self.width // 2, self.height - 22, text=f"⏮ Prev     {play_sym}     Next ⏭", fill="#FFFFFF", font=("Segoe UI", 10, "bold"))
        elif "Audio" in title:
            c.create_text(14, 18, anchor="w", text="AUDIO SPECTRUM (20-BAND)", fill=ac_hex, font=("Segoe UI", 8, "bold"))
            bar_w = max(4, (self.width - 28) // 20 - 3)
            for b_idx, amp in enumerate(self.telemetry.fft_bands):
                bh = max(4, int(amp * (self.height - 36)))
                bx = 14 + b_idx * (bar_w + 3)
                by = self.height - 10
                c.create_rectangle(bx, by - bh, bx + bar_w, by, fill=ac_hex, outline="")
        else:
            c.create_text(self.width // 2, self.height // 2, text=title, fill="#FFFFFF", font=("Segoe UI", 12, "bold"))

    def _draw_metric_card(self, c, label, pct, val_str, ac_hex, design_id):
        c.create_text(14, 22, anchor="w", text=label, fill=ac_hex, font=("Segoe UI", 10, "bold"))
        c.create_text(14, 46, anchor="w", text=val_str, fill="#FFFFFF", font=("Segoe UI", 13, "bold"))
        if design_id == "circular":
            gx, gy = self.width - 42, self.height // 2
            c.create_oval(gx - 24, gy - 24, gx + 24, gy + 24, outline="#2A324B", width=5)
            c.create_arc(gx - 24, gy - 24, gx + 24, gy + 24, start=90, extent=-max(6.0, min(359.0, (pct / 100.0) * 360.0)), style="arc", outline=ac_hex, width=5)
        else:
            bar_w = self.width - 28
            fill_w = max(4, int(bar_w * (max(0.0, min(100.0, pct)) / 100.0)))
            c.create_rectangle(14, self.height - 22, 14 + bar_w, self.height - 12, fill="#222B3A", outline="")
            c.create_rectangle(14, self.height - 22, 14 + fill_w, self.height - 12, fill=ac_hex, outline="")

    def destroy(self):
        try:
            self.win.destroy()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Expandable 24-Hour & 7-Day Weather Forecast Popup Window
# ---------------------------------------------------------------------------
class WeatherForecastPopupWindow:
    def __init__(self, parent_root, on_location_changed=None):
        self.on_location_changed = on_location_changed
        self.win = tk.Toplevel(parent_root)
        self.win.title("Weather Forecast & Locations")
        self.win.geometry("860x640")
        self.win.configure(bg=UI_BG)

        ico_path = os.path.join(REPO_DIR, "assets", "trad-engine.ico")
        if sys.platform == "win32" and os.path.isfile(ico_path):
            try:
                self.win.iconbitmap(ico_path)
            except Exception:
                pass

        self.locations, self.active_idx, self.units = load_weather_config()
        self.forecast_data = None

        top = tk.Frame(self.win, bg=UI_HEADER_BG, padx=14, pady=10)
        top.pack(fill="x")

        tk.Button(
            top, text="↻", bg=UI_CARD_ALT, fg=UI_TEXT, relief="flat", padx=8, pady=4,
            font=("Segoe UI", 10, "bold"), command=lambda: self.refresh_forecast(force=True)
        ).pack(side="left", padx=(0, 8))

        self.loc_var = tk.StringVar(value=self.locations[self.active_idx]["name"])
        self.loc_combo = ttk.Combobox(top, textvariable=self.loc_var, values=[l["name"] for l in self.locations], state="readonly", width=30)
        self.loc_combo.pack(side="left", padx=4)
        self.loc_combo.bind("<<ComboboxSelected>>", self._on_loc_selected)

        self.search_var = tk.StringVar()
        search_entry = tk.Entry(top, textvariable=self.search_var, bg=UI_CARD_BG, fg=UI_TEXT, insertbackground=UI_TEXT, relief="flat", width=22)
        search_entry.pack(side="left", padx=(14, 4), ipady=4)
        search_entry.bind("<Return>", lambda _e: self._on_search())
        tk.Button(
            top, text="Search & Add Village", bg=UI_PURPLE, fg=UI_TEXT, relief="flat",
            padx=12, pady=4, font=("Segoe UI", 9, "bold"), command=self._on_search
        ).pack(side="left", padx=4)

        self.unit_var = tk.StringVar(value="°F" if self.units == "imperial" else "°C")
        unit_cb = ttk.Combobox(top, textvariable=self.unit_var, values=["°C", "°F"], state="readonly", width=4)
        unit_cb.pack(side="right")
        unit_cb.bind("<<ComboboxSelected>>", self._on_unit_changed)

        self.search_frame = tk.Frame(self.win, bg=UI_CARD_BG, padx=14, pady=6)

        hero = tk.Frame(self.win, bg=UI_CARD_BG, padx=18, pady=14, highlightthickness=1, highlightbackground=UI_BORDER)
        hero.pack(fill="x", padx=18, pady=(12, 8))
        self.lbl_place = tk.Label(hero, text="Loading...", bg=UI_CARD_BG, fg=UI_TEXT, font=("Segoe UI", 16, "bold"))
        self.lbl_place.pack(anchor="w")
        self.lbl_temp = tk.Label(hero, text="--°", bg=UI_CARD_BG, fg=UI_AMBER, font=("Segoe UI", 26, "bold"))
        self.lbl_temp.pack(anchor="w")
        self.lbl_details = tk.Label(hero, text="Fetching forecast...", bg=UI_CARD_BG, fg=UI_DIM, font=("Segoe UI", 9))
        self.lbl_details.pack(anchor="w")

        tk.Label(self.win, text="Hourly Forecast (Next 24 Hours)", bg=UI_BG, fg=UI_TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=18)
        self.curve_canvas = tk.Canvas(self.win, height=180, bg="#191622", highlightthickness=1, highlightbackground=UI_BORDER)
        self.curve_canvas.pack(fill="x", padx=18, pady=6)
        self.curve_canvas.bind("<Configure>", lambda _e: self._draw_hourly_curve())

        tk.Label(self.win, text="7-Day Forecast", bg=UI_BG, fg=UI_TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=18, pady=(6, 2))
        self.daily_frame = tk.Frame(self.win, bg=UI_CARD_BG, padx=14, pady=8, highlightthickness=1, highlightbackground=UI_BORDER)
        self.daily_frame.pack(fill="both", expand=True, padx=18, pady=(0, 14))
        self.daily_labels = []
        for idx in range(7):
            row = tk.Frame(self.daily_frame, bg=UI_CARD_BG)
            row.pack(fill="x", pady=3)
            l_day = tk.Label(row, text="--", bg=UI_CARD_BG, fg=UI_TEXT, font=("Segoe UI", 10, "bold"), width=22, anchor="w")
            l_day.pack(side="left")
            l_cond = tk.Label(row, text="--", bg=UI_CARD_BG, fg=UI_DIM, font=("Segoe UI", 9), width=32, anchor="w")
            l_cond.pack(side="left")
            l_range = tk.Label(row, text="--", bg=UI_CARD_BG, fg=UI_AMBER, font=("Segoe UI", 10, "bold"), anchor="e")
            l_range.pack(side="right")
            self.daily_labels.append((l_day, l_cond, l_range))
            if idx < 6:
                tk.Frame(self.daily_frame, height=1, bg=UI_DIVIDER).pack(fill="x")

        self.refresh_forecast(force=False)

    def _on_unit_changed(self, _e=None):
        self.units = "imperial" if self.unit_var.get() == "°F" else "metric"
        save_weather_config(self.locations, self.active_idx, self.units)
        self.refresh_forecast(force=True)
        if self.on_location_changed:
            self.on_location_changed()

    def _on_loc_selected(self, _e=None):
        sel_name = self.loc_var.get()
        for idx, loc in enumerate(self.locations):
            if loc["name"] == sel_name:
                self.active_idx = idx
                save_weather_config(self.locations, self.active_idx, self.units)
                self.refresh_forecast(force=False)
                if self.on_location_changed:
                    self.on_location_changed()
                break

    def _on_search(self):
        q = self.search_var.get().strip()
        if not q:
            return
        self.lbl_details.configure(text=f"Searching '{q}' across ArcGIS World Geocoder & Open-Meteo...")

        def _worker():
            matches = search_village_or_city(q)
            self.win.after(0, lambda: self._show_search_results(matches))

        threading.Thread(target=_worker, daemon=True).start()

    def _show_search_results(self, matches):
        for w in self.search_frame.winfo_children():
            w.destroy()
        if not matches:
            self.lbl_details.configure(text="No matching village/city found. Try entering 'lat, lon' coordinates.")
            return
        self.search_frame.pack(fill="x", padx=18, pady=4, before=self.curve_canvas)
        tk.Label(self.search_frame, text="Click a result to add & activate:", bg=UI_CARD_BG, fg=UI_PURPLE_HOVER, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        for m in matches[:5]:
            tk.Button(
                self.search_frame,
                text=f"＋ {m['name']}  ({m['lat']:.4f}, {m['lon']:.4f} • {m['source']})",
                bg=UI_CARD_ALT, fg=UI_TEXT, relief="flat", anchor="w", padx=8, pady=3,
                command=lambda item=m: self._add_and_use_location(item),
            ).pack(fill="x", pady=1)

    def _add_and_use_location(self, item):
        self.search_frame.pack_forget()
        existing = next((i for i, l in enumerate(self.locations) if l["name"].lower() == item["name"].lower()), None)
        if existing is not None:
            self.active_idx = existing
        else:
            self.locations.insert(0, {"name": item["name"], "lat": item["lat"], "lon": item["lon"]})
            self.active_idx = 0
        save_weather_config(self.locations, self.active_idx, self.units)
        self.loc_combo.configure(values=[l["name"] for l in self.locations])
        self.loc_var.set(self.locations[self.active_idx]["name"])
        self.refresh_forecast(force=False)
        if self.on_location_changed:
            self.on_location_changed()

    def refresh_forecast(self, force=False):
        loc = self.locations[self.active_idx]
        self.lbl_place.configure(text=loc["name"])
        self.lbl_details.configure(text="Updating forecast...")

        def _worker():
            try:
                data = fetch_full_weather_forecast(loc["lat"], loc["lon"], units=self.units, force=force)
                self.win.after(0, lambda: self._apply_forecast(loc, data))
            except Exception as e:
                self.win.after(0, lambda: self.lbl_details.configure(text=f"Could not fetch weather: {e}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_forecast(self, loc, data):
        if not self.win.winfo_exists():
            return
        self.forecast_data = data
        cur = data.get("current", {})
        daily = data.get("daily", {})
        is_imp = self.units == "imperial"
        t_sym = "°F" if is_imp else "°C"
        w_sym = "mph" if is_imp else "km/h"
        temp = round(float(cur.get("temperature_2m", 0)))
        cond = wmo_code_to_description(cur.get("weather_code", 0))
        hum = round(float(cur.get("relative_humidity_2m", 0)))
        pop = round(float(cur.get("precipitation_probability", 0)))
        wind = round(float(cur.get("wind_speed_10m", 0)))
        wdir = deg_to_cardinal(cur.get("wind_direction_10m", 0))

        self.lbl_place.configure(text=loc["name"])
        self.lbl_temp.configure(text=f"{temp}{t_sym}  •  {cond}")
        self.lbl_details.configure(text=f"Humidity: {hum}%   •   Rain Chance: {pop}%   •   Wind: {wind} {w_sym} ({wdir})   •   ({loc['lat']:.4f}, {loc['lon']:.4f})")
        self._draw_hourly_curve()

        d_times = daily.get("time", [])
        d_codes = daily.get("weather_code", [])
        d_max = daily.get("temperature_2m_max", [])
        d_min = daily.get("temperature_2m_min", [])
        d_pop = daily.get("precipitation_probability_max", [])
        for i in range(7):
            l_day, l_cond, l_range = self.daily_labels[i]
            if i < len(d_times):
                try:
                    dt = datetime.date.fromisoformat(d_times[i])
                    day_str = "Today" if i == 0 else dt.strftime("%A, %b %d")
                except Exception:
                    day_str = d_times[i]
                c_txt = wmo_code_to_description(d_codes[i] if i < len(d_codes) else 0)
                p_txt = f"Rain chance {round(float(d_pop[i]))}%" if i < len(d_pop) else ""
                lo_v = round(float(d_min[i])) if i < len(d_min) else "--"
                hi_v = round(float(d_max[i])) if i < len(d_max) else "--"
                l_day.configure(text=day_str)
                l_cond.configure(text=f"{c_txt}  •  {p_txt}")
                l_range.configure(text=f"Low {lo_v}{t_sym}  →  High {hi_v}{t_sym}")

    def _draw_hourly_curve(self):
        c = self.curve_canvas
        c.delete("all")
        if not self.forecast_data:
            return
        hourly = self.forecast_data.get("hourly", {})
        times = hourly.get("time", [])[:12]
        temps = [float(x) for x in hourly.get("temperature_2m", [])[:12]]
        pops = [int(float(x)) for x in hourly.get("precipitation_probability", [])[:12]]
        if len(temps) < 2:
            return
        w = max(600, c.winfo_width())
        h = max(160, c.winfo_height())
        pad_x = 38
        step_x = (w - 2 * pad_x) / (len(temps) - 1)
        t_min, t_max = min(temps), max(temps)
        t_span = max(2.0, t_max - t_min)
        pts = []
        for i, tv in enumerate(temps):
            px = pad_x + i * step_x
            py = 56 + (1.0 - (tv - t_min) / t_span) * (h - 90)
            pts.append((px, py))
            t_lbl = "Now" if i == 0 else (times[i].split("T")[-1][:5] if i < len(times) else "")
            c.create_text(px, 16, text=t_lbl, fill=UI_TEXT, font=("Segoe UI", 8))
            if i < len(pops):
                c.create_text(px, 32, text=f"{pops[i]}%", fill="#38BDF8", font=("Segoe UI", 8, "bold"))
            c.create_text(px, h - 14, text=f"{round(tv)}°", fill=UI_AMBER, font=("Segoe UI", 9, "bold"))
        for i in range(len(pts) - 1):
            c.create_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], fill=UI_AMBER, width=2.5)
        for px, py in pts:
            c.create_oval(px - 3, py - 3, px + 3, py + 3, fill=UI_AMBER, outline="#FFFFFF")


# ---------------------------------------------------------------------------
# Main Trad Desktop Control Center (Matching Linux GTK4 / Libadwaita UI)
# ---------------------------------------------------------------------------
class TradDesktopWindowsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Trad Desktop")
        self.root.geometry("1120x760")
        self.root.minsize(920, 620)
        self.root.configure(bg=UI_BG)

        ico_path = os.path.join(REPO_DIR, "assets", "trad-engine.ico")
        if sys.platform == "win32" and os.path.isfile(ico_path):
            try:
                self.root.iconbitmap(ico_path)
            except Exception:
                pass

        self.monitors = detect_monitors(self.root)
        self.telemetry = SystemTelemetryBackend()
        self.skins = discover_all_skins()
        self.custom_suites = discover_custom_suites()
        self.skin_state = load_global_config(self.skins)
        self.active_custom_suite_id = None
        self.basic_theme_idx, self.basic_shape_idx, self.basic_design_idx = read_current_basic_style()
        self.weather_locations, self.weather_active_idx, self.weather_units = load_weather_config()
        save_weather_config(self.weather_locations, self.weather_active_idx, self.weather_units)

        self.active_desktop_windows = []
        self.engine_running = True
        self.selected_key = next((s["key"] for s in self.skins if not s["is_suite"]), self.skins[0]["key"] if self.skins else None)
        self.keep_other_monitors_active = False
        self.suite_monitor_idx = 0
        self._detect_active_custom_suite()
        for s in self.skins:
            if self.skin_state[s["key"]]["active"]:
                self.suite_monitor_idx = self.skin_state[s["key"]]["monitor"]
                break

        self.current_tab = "suites"
        self.manual_loc_expanded = False
        self.saved_loc_expanded = False
        self.weather_search_results = []
        self._toast_after_id = None

        self._configure_ttk_styles()
        self._build_shell()
        self._switch_tab("suites")
        self.relaunch_desktop_widgets()
        self._schedule_tick()

    def _configure_ttk_styles(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "TCombobox",
            fieldbackground=UI_CARD_ALT,
            background=UI_CARD_ALT,
            foreground=UI_TEXT,
            bordercolor=UI_BORDER,
            arrowcolor=UI_TEXT,
            selectbackground=UI_PURPLE,
            selectforeground=UI_TEXT,
            padding=5,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", UI_CARD_ALT)],
            selectbackground=[("readonly", UI_CARD_ALT)],
            selectforeground=[("readonly", UI_TEXT)],
        )
        style.configure("Vertical.TScrollbar", background=UI_CARD_ALT, troughcolor=UI_BG, bordercolor=UI_BG, arrowcolor=UI_DIM)

    # --- Shell: Libadwaita Header Bar + Centered View Switcher + Toast ---
    def _build_shell(self):
        header = tk.Frame(self.root, bg=UI_HEADER_BG, height=48, padx=10, pady=7)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Left Cluster: Purple Install Pill, Folder, Refresh, Export .rmskin
        left_bar = tk.Frame(header, bg=UI_HEADER_BG)
        left_bar.pack(side="left")

        tk.Button(
            left_bar, text="Install Skin / .ini…", bg=UI_PURPLE, fg=UI_TEXT,
            activebackground=UI_PURPLE_HOVER, activeforeground=UI_TEXT,
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4,
            cursor="hand2", command=self._on_install_skin
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            left_bar, text="📁", bg=UI_HEADER_BG, fg=UI_TEXT, activebackground=UI_CARD_ALT,
            activeforeground=UI_TEXT, font=("Segoe UI", 10), relief="flat", padx=7, pady=3,
            cursor="hand2", command=self._on_open_skins_folder
        ).pack(side="left", padx=2)

        tk.Button(
            left_bar, text="↻", bg=UI_HEADER_BG, fg=UI_TEXT, activebackground=UI_CARD_ALT,
            activeforeground=UI_TEXT, font=("Segoe UI", 11), relief="flat", padx=7, pady=2,
            cursor="hand2", command=self._on_refresh_all
        ).pack(side="left", padx=2)

        tk.Button(
            left_bar, text="📦 Export .rmskin", bg=UI_CARD_ALT, fg=UI_TEXT, activebackground=UI_CARD_HOVER,
            activeforeground=UI_TEXT, font=("Segoe UI", 8, "bold"), relief="flat", padx=9, pady=4,
            cursor="hand2", command=self._on_export_rmskin
        ).pack(side="left", padx=(6, 0))

        # Center Cluster: 3-Tab View Switcher
        center_bar = tk.Frame(header, bg=UI_HEADER_BG)
        center_bar.place(relx=0.5, rely=0.5, anchor="center")

        self.tab_btns = {}
        for tid, lbl in [("suites", "🖼  Suites"), ("basic", "⊞  Basic Widgets"), ("widgets", "✥  Widgets & Position")]:
            btn = tk.Button(
                center_bar, text=lbl, bg=UI_HEADER_BG, fg=UI_DIM,
                activebackground=UI_CARD_HOVER, activeforeground=UI_TEXT,
                font=("Segoe UI", 9, "bold"), relief="flat", padx=14, pady=5,
                cursor="hand2", command=lambda k=tid: self._switch_tab(k)
            )
            btn.pack(side="left", padx=3)
            self.tab_btns[tid] = btn

        # Right Cluster: Status + Turn OFF Button
        right_bar = tk.Frame(header, bg=UI_HEADER_BG)
        right_bar.pack(side="right")

        self.power_btn = tk.Button(
            right_bar, text="Turn OFF", bg=UI_RED_BG, fg=UI_RED_FG,
            activebackground="#6E2B37", activeforeground="#FFFFFF",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=14, pady=4,
            cursor="hand2", command=self._on_toggle_power
        )
        self.power_btn.pack(side="right", padx=(8, 0))

        self.status_label = tk.Label(
            right_bar, text="● Running", bg=UI_HEADER_BG, fg=UI_GREEN_FG, font=("Segoe UI", 9)
        )
        self.status_label.pack(side="right")

        tk.Frame(self.root, height=1, bg=UI_DIVIDER).pack(fill="x")

        # Content Stage
        self.stage = tk.Frame(self.root, bg=UI_BG)
        self.stage.pack(fill="both", expand=True)

        self.tab_frames = {
            "suites": tk.Frame(self.stage, bg=UI_BG),
            "basic": tk.Frame(self.stage, bg=UI_BG),
            "widgets": tk.Frame(self.stage, bg=UI_BG),
        }

        self._build_suites_tab()
        self._build_basic_tab()
        self._build_widgets_tab()

        # Floating Toast Banner (Adw.ToastOverlay equivalent)
        self.toast_lbl = tk.Label(
            self.root, text="", bg="#3A3548", fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"), padx=18, pady=8,
            highlightthickness=1, highlightbackground=UI_BORDER
        )

    def _show_toast(self, message):
        self.toast_lbl.configure(text=message)
        self.toast_lbl.place(relx=0.5, rely=0.95, anchor="s")
        if self._toast_after_id:
            self.root.after_cancel(self._toast_after_id)
        self._toast_after_id = self.root.after(2800, self.toast_lbl.place_forget)

    def _switch_tab(self, tab_id):
        self.current_tab = tab_id
        for tid, fr in self.tab_frames.items():
            fr.pack_forget()
            b = self.tab_btns[tid]
            if tid == tab_id:
                b.configure(bg=UI_CARD_ALT, fg=UI_TEXT)
            else:
                b.configure(bg=UI_HEADER_BG, fg=UI_DIM)
        self.tab_frames[tab_id].pack(fill="both", expand=True)
        if tab_id == "widgets":
            self._draw_monitor_preview()

    # Helpers for Libadwaita PreferencesGroup-style Boxed Cards
    def _make_group(self, parent, title, description):
        outer = tk.Frame(parent, bg=UI_BG)
        outer.pack(fill="x", pady=(0, 18))
        tk.Label(outer, text=title, bg=UI_BG, fg=UI_TEXT, font=("Segoe UI", 11, "bold"), anchor="w").pack(fill="x")
        if description:
            tk.Label(outer, text=description, bg=UI_BG, fg=UI_DIM, font=("Segoe UI", 9), anchor="w", justify="left", wraplength=780).pack(fill="x", pady=(2, 8))
        card = tk.Frame(outer, bg=UI_CARD_BG, highlightthickness=1, highlightbackground=UI_BORDER)
        card.pack(fill="x")
        return card

    def _make_row(self, card, title, subtitle="", is_last=False):
        row = tk.Frame(card, bg=UI_CARD_BG, padx=14, pady=10)
        row.pack(fill="x")
        left = tk.Frame(row, bg=UI_CARD_BG)
        left.pack(side="left", fill="x", expand=True, padx=(0, 12))
        lbl_title = tk.Label(left, text=title, bg=UI_CARD_BG, fg=UI_TEXT, font=("Segoe UI", 10, "bold"), anchor="w")
        lbl_title.pack(fill="x")
        lbl_sub = None
        if subtitle:
            lbl_sub = tk.Label(left, text=subtitle, bg=UI_CARD_BG, fg=UI_DIM, font=("Segoe UI", 8), anchor="w", justify="left", wraplength=540)
            lbl_sub.pack(fill="x", pady=(1, 0))
        right = tk.Frame(row, bg=UI_CARD_BG)
        right.pack(side="right")
        if not is_last:
            tk.Frame(card, height=1, bg=UI_DIVIDER).pack(fill="x")
        return row, right, lbl_title, lbl_sub

    def _get_monitor_dropdown_names(self):
        names = [m["name"] for m in self.monitors]
        if len(self.monitors) > 1:
            names.append("All Monitors (Both 1st and 2nd Monitor)")
        return names

    def _dropdown_name_to_mon_val(self, name):
        names = [m["name"] for m in self.monitors]
        if name in names:
            return names.index(name)
        if len(self.monitors) > 1:
            return -1
        return 0

    def _mon_val_to_dropdown_name(self, mon_val):
        names = self._get_monitor_dropdown_names()
        if mon_val == -1 and len(self.monitors) > 1:
            return names[-1]
        idx = max(0, min(len(self.monitors) - 1, int(mon_val)))
        return names[idx]

    def _detect_active_custom_suite(self):
        active_non_suite = {s["key"] for s in self.skins if not s["is_suite"] and self.skin_state[s["key"]]["active"]}
        if not active_non_suite:
            return
        for cs in self.custom_suites:
            cs_keys = set()
            for w in cs["widgets"]:
                wkey = w.get("key", "")
                matched = next((s["key"] for s in self.skins if s["key"] == wkey or s["key"].endswith(os.path.basename(wkey))), None)
                if matched:
                    cs_keys.add(matched)
            if cs_keys and cs_keys == active_non_suite:
                self.active_custom_suite_id = cs["id"]
                return

    # =========================================================================
    # TAB 1: SUITES (Clamped Centered Cards Matching Linux)
    # =========================================================================
    def _build_suites_tab(self):
        root_fr = self.tab_frames["suites"]
        for w in root_fr.winfo_children():
            w.destroy()

        scroll = ScrollableFrame(root_fr, bg=UI_BG)
        scroll.pack(fill="both", expand=True)

        clamp = tk.Frame(scroll.inner, bg=UI_BG, width=800)
        clamp.pack(pady=20, padx=24, fill="x", anchor="n")

        # Group 1: Suite Display Settings
        mon_card = self._make_group(
            clamp,
            "Suite Display Settings",
            "Choose which monitor displays your suite (Monitor 0, Monitor 1, or Both Monitors), or keep each monitor's layout independent.",
        )
        _r, right, _lt, _ls = self._make_row(
            mon_card,
            "Target Monitor for Suite",
            "Changing the monitor immediately moves or mirrors and auto-scales the active suite",
            is_last=False,
        )
        mon_names = self._get_monitor_dropdown_names()
        self.suite_mon_var = tk.StringVar(value=self._mon_val_to_dropdown_name(self.suite_monitor_idx))
        mon_cb = ttk.Combobox(right, textvariable=self.suite_mon_var, values=mon_names, state="readonly", width=32)
        mon_cb.pack(side="left", padx=(0, 6))
        mon_cb.bind("<<ComboboxSelected>>", self._on_suite_monitor_changed)
        if len(self.monitors) > 1:
            tk.Button(
                right, text="Mirror on Both Monitors", bg=UI_CARD_ALT, fg=UI_TEXT,
                font=("Segoe UI", 8, "bold"), relief="flat", padx=10, pady=4,
                cursor="hand2", command=self._on_mirror_both_monitors_clicked
            ).pack(side="left")

        _r2, right2, _lt2, _ls2 = self._make_row(
            mon_card,
            "Keep Other Monitor's Widgets Active (Multi-Monitor Pinning)",
            "Enable to place different suites or widgets on 1st and 2nd monitor without clearing the other monitor",
            is_last=True,
        )
        PillSwitch(right2, initial=self.keep_other_monitors_active, command=lambda val: setattr(self, "keep_other_monitors_active", bool(val))).pack()

        # Group 2: Built-in and Saved Custom Suites
        suites_card = self._make_group(
            clamp,
            "Built-in and Saved Custom Suites",
            "Click 'Activate Suite' on any suite to replace the active desktop layout, or build a new suite from Basic or Custom Widgets.",
        )

        builtin_suites = [s for s in self.skins if s["is_suite"]]
        total_items = len(builtin_suites) + len(self.custom_suites)
        idx = 0

        for s in builtin_suites:
            idx += 1
            is_act = self.skin_state[s["key"]]["active"] and self.active_custom_suite_id is None
            _row, right, _lt, _ls = self._make_row(
                suites_card,
                s["title"],
                f"Built-in Suite • {s['subtitle']} ({s['est_w']}×{s['est_h']}, Auto-Fits Monitor)",
                is_last=(idx == total_items),
            )
            tk.Button(
                right,
                text="Active ✓" if is_act else "Activate Suite",
                bg=UI_PURPLE if is_act else UI_CARD_ALT,
                fg=UI_TEXT,
                activebackground=UI_PURPLE_HOVER,
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                padx=14,
                pady=4,
                cursor="hand2",
                command=lambda k=s["key"]: self._activate_suite(k),
            ).pack(side="left", padx=(0, 6))

            tk.Button(
                right,
                text="🛠",
                bg=UI_CARD_ALT,
                fg=UI_TEXT,
                font=("Segoe UI", 9),
                relief="flat",
                padx=8,
                pady=4,
                cursor="hand2",
                command=lambda k=s["key"]: self._jump_to_positioner(k),
            ).pack(side="left")

        for cs in self.custom_suites:
            idx += 1
            is_act = self.active_custom_suite_id == cs["id"]
            w_names = ", ".join(w.get("title", "Widget") for w in cs["widgets"][:5])
            if len(cs["widgets"]) > 5:
                w_names += f", +{len(cs['widgets']) - 5} more"
            _row, right, _lt, _ls = self._make_row(
                suites_card,
                cs["title"],
                f"Custom Suite ({len(cs['widgets'])} widgets: {w_names})",
                is_last=(idx == total_items),
            )
            tk.Button(
                right,
                text="Active ✓" if is_act else "Activate Suite",
                bg=UI_PURPLE if is_act else UI_CARD_ALT,
                fg=UI_TEXT,
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                padx=14,
                pady=4,
                cursor="hand2",
                command=lambda item=cs: self._activate_custom_suite(item),
            ).pack(side="left", padx=(0, 6))

            tk.Button(
                right, text="🛠", bg=UI_CARD_ALT, fg=UI_TEXT, font=("Segoe UI", 9),
                relief="flat", padx=8, pady=4, cursor="hand2",
                command=lambda item=cs: self._edit_custom_suite(item)
            ).pack(side="left", padx=(0, 4))

            tk.Button(
                right, text="🗑", bg=UI_CARD_BG, fg=UI_DIM, font=("Segoe UI", 9),
                relief="flat", padx=6, pady=4, cursor="hand2",
                command=lambda item=cs: self._delete_custom_suite(item)
            ).pack(side="left")

    def _on_mirror_both_monitors_clicked(self):
        if len(self.monitors) > 1:
            names = self._get_monitor_dropdown_names()
            self.suite_mon_var.set(names[-1])
            self._on_suite_monitor_changed()

    def _on_suite_monitor_changed(self, _e=None):
        self.suite_monitor_idx = self._dropdown_name_to_mon_val(self.suite_mon_var.get())
        if self.active_custom_suite_id is not None:
            cs = next((c for c in self.custom_suites if c["id"] == self.active_custom_suite_id), None)
            if cs:
                self._activate_custom_suite(cs, override_monitor=self.suite_monitor_idx)
                return
        target_mons = list(range(len(self.monitors))) if self.suite_monitor_idx == -1 else [self.suite_monitor_idx]
        for s in self.skins:
            if self.skin_state[s["key"]]["active"]:
                self.skin_state[s["key"]]["monitor"] = self.suite_monitor_idx
                self.skin_state[s["key"]]["monitors"] = list(target_mons)
                self.skin_state[s["key"]]["auto_fit"] = True
        save_global_config(self.skins, self.skin_state, len(self.monitors))
        self.relaunch_desktop_widgets()

    def _activate_suite(self, suite_key):
        self.active_custom_suite_id = None
        target_mons = list(range(len(self.monitors))) if self.suite_monitor_idx == -1 else [self.suite_monitor_idx]
        for s in self.skins:
            st = self.skin_state[s["key"]]
            is_t = s["key"] == suite_key
            if is_t:
                st["active"] = True
                if self.keep_other_monitors_active and st.get("monitors"):
                    merged = sorted(list(set(st["monitors"] + target_mons)))
                    st["monitors"] = merged
                    st["monitor"] = -1 if len(merged) > 1 else merged[0]
                else:
                    st["monitors"] = list(target_mons)
                    st["monitor"] = self.suite_monitor_idx
                st["auto_fit"] = True
                st["use_custom_pos"] = False
                st["anchor_x"] = "center"
                st["anchor_y"] = "center"
                st["x"] = 0
                st["y"] = 0
            elif self.keep_other_monitors_active and st.get("active"):
                cur_mons = get_active_monitors_for_skin(st, len(self.monitors))
                rem_mons = [m for m in cur_mons if m not in target_mons]
                st["monitors"] = rem_mons
                if not rem_mons:
                    st["active"] = False
                else:
                    st["monitor"] = -1 if len(rem_mons) > 1 else rem_mons[0]
            else:
                st["active"] = False
                st["monitors"] = []
        save_global_config(self.skins, self.skin_state, len(self.monitors))
        self._build_suites_tab()
        self._build_basic_tab()
        self._build_widgets_tab()
        self.relaunch_desktop_widgets()
        self._show_toast("Suite activated on desktop")

    def _activate_custom_suite(self, cs, override_monitor=None):
        self.active_custom_suite_id = cs["id"]
        target_mon_val = override_monitor if override_monitor is not None else self.suite_monitor_idx
        target_mons = list(range(len(self.monitors))) if target_mon_val == -1 else [target_mon_val]
        suite_matched_keys = set()
        for w in cs["widgets"]:
            wkey = w.get("key", "")
            matched = next((s["key"] for s in self.skins if s["key"] == wkey or s["key"].endswith(os.path.basename(wkey))), None)
            if matched:
                suite_matched_keys.add(matched)
        for s in self.skins:
            if s["key"] in suite_matched_keys:
                continue
            st = self.skin_state[s["key"]]
            if self.keep_other_monitors_active and st.get("active"):
                cur_mons = get_active_monitors_for_skin(st, len(self.monitors))
                rem_mons = [m for m in cur_mons if m not in target_mons]
                st["monitors"] = rem_mons
                if not rem_mons:
                    st["active"] = False
                else:
                    st["monitor"] = -1 if len(rem_mons) > 1 else rem_mons[0]
            else:
                st["active"] = False
                st["monitors"] = []
        for w in cs["widgets"]:
            wkey = w.get("key", "")
            matched = next((s["key"] for s in self.skins if s["key"] == wkey or s["key"].endswith(os.path.basename(wkey))), None)
            if matched:
                st = self.skin_state[matched]
                if self.keep_other_monitors_active and st.get("active"):
                    cur_mons = get_active_monitors_for_skin(st, len(self.monitors))
                    merged = sorted(list(set(cur_mons + target_mons)))
                    st["monitors"] = merged
                    st["monitor"] = -1 if len(merged) > 1 else merged[0]
                else:
                    st["monitors"] = list(target_mons)
                    st["monitor"] = target_mon_val
                st["active"] = True
                st["anchor_x"] = w.get("anchor_x", st["anchor_x"])
                st["anchor_y"] = w.get("anchor_y", st["anchor_y"])
                st["use_custom_pos"] = w.get("use_custom_pos", False)
                st["x"] = w.get("x", 0)
                st["y"] = w.get("y", 0)
                st["ref_w"] = int(w.get("ref_width", 1366))
                st["ref_h"] = int(w.get("ref_height", 768))
                st["auto_fit"] = w.get("auto_fit", True)
                st["scale"] = w.get("scale", 1.0)
        save_global_config(self.skins, self.skin_state, len(self.monitors))
        self._build_suites_tab()
        self._build_basic_tab()
        self._build_widgets_tab()
        self.relaunch_desktop_widgets()
        self._show_toast(f"Activated custom suite '{cs['title']}'")

    def _edit_custom_suite(self, cs):
        self._activate_custom_suite(cs)
        self.new_suite_var.set(cs["title"])
        self._switch_tab("widgets")

    def _delete_custom_suite(self, cs):
        suite_dir = os.path.dirname(cs["manifest_path"])
        try:
            if os.path.isdir(suite_dir) and os.path.abspath(suite_dir).startswith(os.path.abspath(SUITES_DIR)):
                shutil.rmtree(suite_dir)
            if self.active_custom_suite_id == cs["id"]:
                self.active_custom_suite_id = None
            self.custom_suites = discover_custom_suites()
            self._build_suites_tab()
            self._show_toast(f"Deleted custom suite '{cs['title']}'")
        except Exception as e:
            self._show_toast(f"Could not delete suite: {e}")

    # =========================================================================
    # TAB 2: BASIC WIDGETS, THEME STUDIO, WEATHER MANAGER & MEDIA
    # =========================================================================
    def _build_basic_tab(self):
        root_fr = self.tab_frames["basic"]
        for w in root_fr.winfo_children():
            w.destroy()

        scroll = ScrollableFrame(root_fr, bg=UI_BG)
        scroll.pack(fill="both", expand=True)

        clamp = tk.Frame(scroll.inner, bg=UI_BG, width=840)
        clamp.pack(pady=18, padx=24, fill="x", anchor="n")

        # 1. Theme, Shape & Design Studio Group
        studio_group = tk.Frame(clamp, bg=UI_BG)
        studio_group.pack(fill="x", pady=(0, 14))
        tk.Label(studio_group, text="Trad Desktop — Theme, Shape and Design Studio", bg=UI_BG, fg=UI_TEXT, font=("Segoe UI", 11, "bold"), anchor="w").pack(fill="x")
        tk.Label(
            studio_group,
            text="Customize Color Theme, Card Shape (Rounded, Squircle, Pill Capsule, Circular, Borderless), and Gauge Design (Vertical Bars, Circular Rings, Capsule Pill, Horizontal Minimal).",
            bg=UI_BG, fg=UI_DIM, font=("Segoe UI", 9), anchor="w", justify="left", wraplength=800
        ).pack(fill="x", pady=(2, 8))

        studio_card = tk.Frame(studio_group, bg=UI_CARD_BG, highlightthickness=1, highlightbackground=UI_BORDER)
        studio_card.pack(fill="x")

        # Color Theme Row
        _r, right, _lt, self.theme_sub_lbl = self._make_row(studio_card, "Color Theme", BASIC_WIDGET_THEMES[self.basic_theme_idx]["subtitle"])
        self.theme_var = tk.StringVar(value=BASIC_WIDGET_THEMES[self.basic_theme_idx]["name"])
        t_cb = ttk.Combobox(right, textvariable=self.theme_var, values=[t["name"] for t in BASIC_WIDGET_THEMES], state="readonly", width=28)
        t_cb.pack()
        t_cb.bind("<<ComboboxSelected>>", self._on_style_dropdown_changed)

        # Card Shape Row
        _r, right, _lt, self.shape_sub_lbl = self._make_row(studio_card, "Widget Card Shape", BASIC_WIDGET_SHAPES[self.basic_shape_idx]["subtitle"])
        self.shape_var = tk.StringVar(value=BASIC_WIDGET_SHAPES[self.basic_shape_idx]["name"])
        s_cb = ttk.Combobox(right, textvariable=self.shape_var, values=[s["name"] for s in BASIC_WIDGET_SHAPES], state="readonly", width=28)
        s_cb.pack()
        s_cb.bind("<<ComboboxSelected>>", self._on_style_dropdown_changed)

        # Design Row
        _r, right, _lt, self.design_sub_lbl = self._make_row(studio_card, "Widget Design and Gauge Layout", BASIC_WIDGET_DESIGNS[self.basic_design_idx]["subtitle"], is_last=True)
        self.design_var = tk.StringVar(value=BASIC_WIDGET_DESIGNS[self.basic_design_idx]["name"])
        d_cb = ttk.Combobox(right, textvariable=self.design_var, values=[d["name"] for d in BASIC_WIDGET_DESIGNS], state="readonly", width=28)
        d_cb.pack()
        d_cb.bind("<<ComboboxSelected>>", self._on_style_dropdown_changed)

        # Live Theme Swatch Preview Strip (Exact 4-Card Strip Matching Screenshot)
        self.swatch_canvas = tk.Canvas(
            studio_group, height=96, bg=UI_CANVAS_BG,
            highlightthickness=1, highlightbackground=UI_BORDER
        )
        self.swatch_canvas.pack(fill="x", pady=(8, 4))
        self.swatch_canvas.bind("<Configure>", lambda _e: self._draw_theme_swatch_preview())
        self._draw_theme_swatch_preview()

        # 10 Quick Theme Buttons Row
        chips_bar = tk.Frame(studio_group, bg=UI_BG)
        chips_bar.pack(pady=(4, 2))
        quick_themes = [
            ("Neon Blue", 0), ("Frosted Glass", 1), ("Transparent", 2), ("Arctic Blue", 3), ("Fedora Cyber", 4),
            ("Aqua Glass", 5), ("Sunset Glow", 6), ("Sapphire", 7), ("Crimson", 8), ("Lime Classic", 9),
        ]
        for q_lbl, q_idx in quick_themes:
            tk.Button(
                chips_bar, text=q_lbl, bg=UI_BG, fg=UI_TEXT, activebackground=UI_CARD_ALT,
                activeforeground=UI_TEXT, font=("Segoe UI", 8, "bold"), relief="flat",
                padx=7, pady=3, cursor="hand2", command=lambda i=q_idx: self._pick_quick_theme(i)
            ).pack(side="left", padx=2)

        # 2. Quick Toolbar
        qbar = tk.Frame(clamp, bg=UI_BG)
        qbar.pack(fill="x", pady=(2, 16))
        tk.Button(
            qbar, text="Enable All 8 Core Widgets", bg=UI_PURPLE, fg=UI_TEXT,
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6,
            cursor="hand2", command=self._enable_all_basic
        ).pack(side="left", padx=(0, 8))
        tk.Button(
            qbar, text="Enable Music + Visualizer", bg=UI_CARD_ALT, fg=UI_TEXT,
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6,
            cursor="hand2", command=self._enable_music_vis
        ).pack(side="left", padx=(0, 8))
        tk.Button(
            qbar, text="Disable All Basic Widgets", bg=UI_CARD_ALT, fg=UI_TEXT,
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6,
            cursor="hand2", command=self._disable_all_basic
        ).pack(side="left")
        tk.Button(
            qbar, text="Positioner →", bg=UI_CARD_ALT, fg=UI_TEXT,
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6,
            cursor="hand2", command=lambda: self._switch_tab("widgets")
        ).pack(side="right")

        # 3. Music Players and Audio Visualizers Card
        media_skins = [s for s in self.skins if s.get("is_basic") and (s["title"].startswith("Music") or s["title"].startswith("Audio"))]
        if media_skins:
            media_card = self._make_group(
                clamp,
                "Music Players and Audio Visualizers",
                "Live media player controls (Spotify, Browser, VLC, Windows Media Player) and real-time 20-band spectrum analyzers.",
            )
            for idx, s in enumerate(media_skins):
                is_on = self.skin_state[s["key"]]["active"]
                _r, right, _lt, _ls = self._make_row(
                    media_card, s["title"], s.get("desc", s["subtitle"]), is_last=(idx == len(media_skins) - 1)
                )
                PillSwitch(right, initial=is_on, command=lambda val, k=s["key"]: self._set_widget_active(k, val)).pack(side="left", padx=(0, 8))
                tk.Button(
                    right, text="🛠", bg=UI_CARD_ALT, fg=UI_TEXT, relief="flat",
                    padx=8, pady=3, cursor="hand2", command=lambda k=s["key"]: self._jump_to_positioner(k)
                ).pack(side="left")

        # 4. Weather Location & Saved Villages / Cities Group
        weather_card = self._make_group(
            clamp,
            "Weather Location and Saved Villages / Cities",
            "Live weather powered by Open-Meteo (with automatic met.no fallback). Select a saved place, search any city/town/village online, or add a custom village using coordinates.",
        )

        # Row 4a: Active Weather Location
        _r, right, _lt, self.weather_active_sub = self._make_row(
            weather_card,
            "Active Weather Location",
            f"{self.weather_locations[self.weather_active_idx]['name']} ({self.weather_locations[self.weather_active_idx]['lat']:.4f}, {self.weather_locations[self.weather_active_idx]['lon']:.4f})",
        )
        self.weather_loc_var = tk.StringVar(value=self.weather_locations[self.weather_active_idx]["name"])
        self.weather_loc_cb = ttk.Combobox(right, textvariable=self.weather_loc_var, values=[l["name"] for l in self.weather_locations], state="readonly", width=26)
        self.weather_loc_cb.pack(side="left", padx=(0, 8))
        self.weather_loc_cb.bind("<<ComboboxSelected>>", self._on_basic_weather_selected)
        tk.Button(
            right, text="Full Forecast", bg=UI_CARD_ALT, fg=UI_TEXT, font=("Segoe UI", 9, "bold"),
            relief="flat", padx=10, pady=4, cursor="hand2", command=self.open_weather_popup
        ).pack(side="left")

        # Row 4b: Units
        _r, right, _lt, _ls = self._make_row(
            weather_card, "Temperature and Wind Units", "Switch between Celsius / km/h (Metric) and Fahrenheit / mph (Imperial)"
        )
        self.weather_units_var = tk.StringVar(value="Imperial (°F, mph)" if self.weather_units == "imperial" else "Metric (°C, km/h)")
        u_cb = ttk.Combobox(right, textvariable=self.weather_units_var, values=["Metric (°C, km/h)", "Imperial (°F, mph)"], state="readonly", width=20)
        u_cb.pack()
        u_cb.bind("<<ComboboxSelected>>", self._on_basic_weather_units_changed)

        # Row 4c: Search City, Town, or Village
        _r, right, _lt, _ls = self._make_row(
            weather_card, "Search City, Town, or Village", "Search online (e.g. Polokwane, Mahatlani, Majosi) or enter latitude, longitude (e.g. -23.31, 30.72)"
        )
        self.basic_weather_search_var = tk.StringVar()
        w_entry = tk.Entry(right, textvariable=self.basic_weather_search_var, bg=UI_CANVAS_BG, fg=UI_TEXT, insertbackground=UI_TEXT, relief="flat", width=24)
        w_entry.pack(side="left", padx=(0, 6), ipady=4)
        w_entry.bind("<Return>", lambda _e: self._on_basic_weather_search())
        tk.Button(
            right, text="Search", bg=UI_PURPLE, fg=UI_TEXT, font=("Segoe UI", 9, "bold"),
            relief="flat", padx=12, pady=4, cursor="hand2", command=self._on_basic_weather_search
        ).pack(side="left")

        # Search Results Container (shown dynamically after search)
        self.basic_search_results_frame = tk.Frame(weather_card, bg=UI_CARD_ALT)

        # Row 4d: Manual Village Coordinates Expander
        _r, right, _lt, _ls = self._make_row(
            weather_card,
            "Add Village or Custom Location Manually",
            "Best for rural villages (e.g. Mahatlani Village) — enter display name and coordinates",
        )
        tk.Button(
            right, text="▾ Enter Coordinates" if not self.manual_loc_expanded else "▴ Hide",
            bg=UI_CARD_ALT, fg=UI_TEXT, font=("Segoe UI", 8, "bold"), relief="flat", padx=10, pady=4,
            cursor="hand2", command=self._toggle_manual_loc_box
        ).pack()

        self.manual_loc_box = tk.Frame(weather_card, bg=UI_CARD_ALT, padx=14, pady=10)
        if self.manual_loc_expanded:
            self.manual_loc_box.pack(fill="x")
        self.manual_name_var = tk.StringVar()
        self.manual_lat_var = tk.StringVar()
        self.manual_lon_var = tk.StringVar()
        mf1 = tk.Frame(self.manual_loc_box, bg=UI_CARD_ALT)
        mf1.pack(fill="x", pady=3)
        tk.Label(mf1, text="Location Name:", bg=UI_CARD_ALT, fg=UI_DIM, width=14, anchor="w").pack(side="left")
        tk.Entry(mf1, textvariable=self.manual_name_var, bg=UI_CANVAS_BG, fg=UI_TEXT, insertbackground=UI_TEXT, relief="flat").pack(side="left", fill="x", expand=True, ipady=3)
        mf2 = tk.Frame(self.manual_loc_box, bg=UI_CARD_ALT)
        mf2.pack(fill="x", pady=3)
        tk.Label(mf2, text="Latitude:", bg=UI_CARD_ALT, fg=UI_DIM, width=14, anchor="w").pack(side="left")
        tk.Entry(mf2, textvariable=self.manual_lat_var, bg=UI_CANVAS_BG, fg=UI_TEXT, insertbackground=UI_TEXT, relief="flat", width=14).pack(side="left", ipady=3, padx=(0, 12))
        tk.Label(mf2, text="Longitude:", bg=UI_CARD_ALT, fg=UI_DIM, anchor="w").pack(side="left", padx=(0, 6))
        tk.Entry(mf2, textvariable=self.manual_lon_var, bg=UI_CANVAS_BG, fg=UI_TEXT, insertbackground=UI_TEXT, relief="flat", width=14).pack(side="left", ipady=3)
        tk.Button(
            mf2, text="Add Village & Activate", bg=UI_PURPLE, fg=UI_TEXT, font=("Segoe UI", 9, "bold"),
            relief="flat", padx=12, pady=3, cursor="hand2", command=self._on_add_manual_weather_location
        ).pack(side="right")

        # Row 4e: Manage Saved Weather Locations
        _r, right, _lt, _ls = self._make_row(
            weather_card,
            "Manage Saved Weather Locations",
            f"{len(self.weather_locations)} saved locations",
            is_last=not self.saved_loc_expanded,
        )
        tk.Button(
            right, text="▾ Show All" if not self.saved_loc_expanded else "▴ Hide",
            bg=UI_CARD_ALT, fg=UI_TEXT, font=("Segoe UI", 8, "bold"), relief="flat", padx=10, pady=4,
            cursor="hand2", command=self._toggle_saved_loc_box
        ).pack()

        if self.saved_loc_expanded:
            saved_box = tk.Frame(weather_card, bg=UI_CARD_ALT, padx=14, pady=8)
            saved_box.pack(fill="x")
            for idx_l, loc in enumerate(self.weather_locations):
                is_cur = idx_l == self.weather_active_idx
                srow = tk.Frame(saved_box, bg=UI_CARD_ALT, pady=3)
                srow.pack(fill="x")
                tk.Label(
                    srow,
                    text=f"{loc['name']}   ({loc['lat']:.4f}, {loc['lon']:.4f})" + ("  •  Active" if is_cur else ""),
                    bg=UI_CARD_ALT, fg=UI_TEXT if is_cur else UI_DIM, font=("Segoe UI", 9, "bold" if is_cur else "normal"), anchor="w"
                ).pack(side="left")
                if len(self.weather_locations) > 1:
                    tk.Button(
                        srow, text="🗑", bg=UI_CARD_ALT, fg=UI_DIM, relief="flat", padx=6,
                        cursor="hand2", command=lambda i=idx_l: self._delete_weather_location(i)
                    ).pack(side="right", padx=(4, 0))
                tk.Button(
                    srow, text="Active ✓" if is_cur else "Use", bg=UI_PURPLE if is_cur else UI_CARD_BG,
                    fg=UI_TEXT, font=("Segoe UI", 8, "bold"), relief="flat", padx=10, pady=2,
                    cursor="hand2", command=lambda i=idx_l: self._set_active_weather_index(i)
                ).pack(side="right")

        # 5. Core System Basic Widgets (8 Anchored Blocks)
        core_skins = [s for s in self.skins if s.get("is_basic") and not (s["title"].startswith("Music") or s["title"].startswith("Audio"))]
        if core_skins:
            core_card = self._make_group(
                clamp,
                "Core System Basic Widgets (8 Anchored Blocks)",
                "Toggle individual anchored system telemetry blocks ON or OFF. Click the tool icon on any block to fine-tune its desktop coordinates.",
            )
            for idx, s in enumerate(core_skins):
                is_on = self.skin_state[s["key"]]["active"]
                _r, right, _lt, _ls = self._make_row(
                    core_card, s["title"], s["subtitle"], is_last=(idx == len(core_skins) - 1)
                )
                PillSwitch(right, initial=is_on, command=lambda val, k=s["key"]: self._set_widget_active(k, val)).pack(side="left", padx=(0, 8))
                tk.Button(
                    right, text="🛠", bg=UI_CARD_ALT, fg=UI_TEXT, relief="flat",
                    padx=8, pady=3, cursor="hand2", command=lambda k=s["key"]: self._jump_to_positioner(k)
                ).pack(side="left")

    def _draw_theme_swatch_preview(self):
        c = self.swatch_canvas
        if not hasattr(self, "swatch_canvas") or not c.winfo_exists():
            return
        c.delete("all")
        w = max(720, c.winfo_width())
        theme = BASIC_WIDGET_THEMES[self.basic_theme_idx]
        shape = BASIC_WIDGET_SHAPES[self.basic_shape_idx]
        design = BASIC_WIDGET_DESIGNS[self.basic_design_idx]

        rad = theme["corner_radius"] if shape["radius"] is None else shape["radius"]
        rad = min(28, rad)
        borderless = shape.get("borderless", False) or theme["name"] == "Pure Transparent"
        bg_hex = theme["bg_hex"]
        bd_hex = theme["border_hex"]
        ac_hex = theme["accent_hex"]

        cards = [
            (18, 12, 155, 72, "CPU", "42%"),
            (188, 12, 195, 72, "08 : 54", "Trad Desktop"),
            (398, 12, 170, 72, "RAM / SWAP", "28% Used"),
            (584, 12, 200, 72, "♫ Imagine Dragons", "⏮  ⏸  ⏭  •  Visualizer"),
        ]
        for idx, (cx, cy, cw, ch, title_txt, sub_txt) in enumerate(cards):
            if cx + cw > w - 10:
                break
            if not borderless:
                draw_round_rect(c, cx, cy, cx + cw, cy + ch, rad, fill=bg_hex, outline=bd_hex, width=1.6)
            if design["id"] == "circular" and idx in (0, 2):
                rx, ry = cx + cw - 30, cy + ch // 2
                c.create_oval(rx - 18, ry - 18, rx + 18, ry + 18, outline="#31394D", width=4)
                c.create_arc(rx - 18, ry - 18, rx + 18, ry + 18, start=90, extent=-210, style="arc", outline=ac_hex, width=4)

            c.create_text(cx + 12, cy + 20, anchor="w", text=title_txt, fill="#FFFFFF", font=("Segoe UI", 9, "bold"))
            c.create_text(cx + 12, cy + 38, anchor="w", text=sub_txt, fill=ac_hex, font=("Segoe UI", 8, "bold"))

            if idx == 3:
                for b in range(12):
                    bh = 5 + ((b * 7) % 16)
                    bx = cx + 12 + b * 14
                    by = cy + 64
                    c.create_rectangle(bx, by - bh, bx + 9, by, fill=ac_hex, outline="")
            elif design["id"] != "circular":
                c.create_rectangle(cx + 12, cy + 54, cx + cw - 12, cy + 59, fill=ac_hex, outline="")

    def _pick_quick_theme(self, idx):
        self.basic_theme_idx = idx
        self.theme_var.set(BASIC_WIDGET_THEMES[idx]["name"])
        self._apply_style_change(f"Theme set to '{BASIC_WIDGET_THEMES[idx]['name']}'")

    def _on_style_dropdown_changed(self, _e=None):
        for i, t in enumerate(BASIC_WIDGET_THEMES):
            if t["name"] == self.theme_var.get():
                self.basic_theme_idx = i
        for i, s in enumerate(BASIC_WIDGET_SHAPES):
            if s["name"] == self.shape_var.get():
                self.basic_shape_idx = i
        for i, d in enumerate(BASIC_WIDGET_DESIGNS):
            if d["name"] == self.design_var.get():
                self.basic_design_idx = i
        self._apply_style_change("Updated Basic Widget theme & design")

    def _apply_style_change(self, toast_msg):
        t = BASIC_WIDGET_THEMES[self.basic_theme_idx]
        s = BASIC_WIDGET_SHAPES[self.basic_shape_idx]
        d = BASIC_WIDGET_DESIGNS[self.basic_design_idx]
        write_basic_theme(t, s, d)
        self.theme_sub_lbl.configure(text=t["subtitle"])
        self.shape_sub_lbl.configure(text=s["subtitle"])
        self.design_sub_lbl.configure(text=d["subtitle"])
        self._draw_theme_swatch_preview()
        self.relaunch_desktop_widgets()
        self._show_toast(toast_msg)

    def _set_widget_active(self, key, active):
        self.skin_state[key]["active"] = bool(active)
        self.active_custom_suite_id = None
        save_global_config(self.skins, self.skin_state)
        self._build_suites_tab()
        self._build_widgets_tab()
        self.relaunch_desktop_widgets()

    def _enable_all_basic(self):
        self.active_custom_suite_id = None
        for s in self.skins:
            if s["is_suite"]:
                self.skin_state[s["key"]]["active"] = False
            elif s.get("is_basic") and s["title"].startswith("Basic"):
                self.skin_state[s["key"]]["active"] = True
        save_global_config(self.skins, self.skin_state)
        self._build_suites_tab()
        self._build_basic_tab()
        self._build_widgets_tab()
        self.relaunch_desktop_widgets()
        self._show_toast("Enabled all 8 Core Basic Widgets")

    def _enable_music_vis(self):
        self.active_custom_suite_id = None
        for s in self.skins:
            if s["is_suite"]:
                self.skin_state[s["key"]]["active"] = False
            elif s["title"] in ("MusicBanner", "AudioVisualizer"):
                self.skin_state[s["key"]]["active"] = True
        save_global_config(self.skins, self.skin_state)
        self._build_suites_tab()
        self._build_basic_tab()
        self._build_widgets_tab()
        self.relaunch_desktop_widgets()
        self._show_toast("Enabled Music Player + Audio Visualizer")

    def _disable_all_basic(self):
        for s in self.skins:
            if s.get("is_basic"):
                self.skin_state[s["key"]]["active"] = False
        save_global_config(self.skins, self.skin_state)
        self._build_basic_tab()
        self._build_widgets_tab()
        self.relaunch_desktop_widgets()
        self._show_toast("Disabled all Basic Widgets")

    # Weather Manager Callbacks in Basic Widgets Tab
    def _set_active_weather_index(self, idx):
        self.weather_active_idx = max(0, min(len(self.weather_locations) - 1, idx))
        save_weather_config(self.weather_locations, self.weather_active_idx, self.weather_units)
        self._build_basic_tab()
        self._on_weather_updated()
        self._show_toast(f"Weather set to '{self.weather_locations[self.weather_active_idx]['name']}'")

    def _on_basic_weather_selected(self, _e=None):
        sel = self.weather_loc_var.get()
        for idx, loc in enumerate(self.weather_locations):
            if loc["name"] == sel:
                self._set_active_weather_index(idx)
                break

    def _on_basic_weather_units_changed(self, _e=None):
        self.weather_units = "imperial" if "Imperial" in self.weather_units_var.get() else "metric"
        save_weather_config(self.weather_locations, self.weather_active_idx, self.weather_units)
        self._on_weather_updated()
        self._show_toast(f"Weather units set to {self.weather_units}")

    def _toggle_manual_loc_box(self):
        self.manual_loc_expanded = not self.manual_loc_expanded
        self._build_basic_tab()

    def _toggle_saved_loc_box(self):
        self.saved_loc_expanded = not self.saved_loc_expanded
        self._build_basic_tab()

    def _on_add_manual_weather_location(self):
        name = self.manual_name_var.get().strip()
        try:
            lat = float(self.manual_lat_var.get().strip())
            lon = float(self.manual_lon_var.get().strip())
        except ValueError:
            self._show_toast("Please enter valid numeric Latitude and Longitude")
            return
        if not name:
            name = f"Village ({lat:.4f}, {lon:.4f})"
        self.weather_locations.insert(0, {"name": name, "lat": lat, "lon": lon})
        self.weather_active_idx = 0
        self.manual_loc_expanded = False
        save_weather_config(self.weather_locations, self.weather_active_idx, self.weather_units)
        self._build_basic_tab()
        self._on_weather_updated()
        self._show_toast(f"Added & activated '{name}'")

    def _delete_weather_location(self, idx):
        if len(self.weather_locations) <= 1:
            return
        removed = self.weather_locations.pop(idx)
        self.weather_active_idx = max(0, min(self.weather_active_idx, len(self.weather_locations) - 1))
        save_weather_config(self.weather_locations, self.weather_active_idx, self.weather_units)
        self._build_basic_tab()
        self._on_weather_updated()
        self._show_toast(f"Removed '{removed['name']}'")

    def _on_basic_weather_search(self):
        q = self.basic_weather_search_var.get().strip()
        if not q:
            return
        self._show_toast(f"Searching for '{q}'...")

        def _worker():
            matches = search_village_or_city(q)
            self.root.after(0, lambda: self._populate_basic_search_results(matches))

        threading.Thread(target=_worker, daemon=True).start()

    def _populate_basic_search_results(self, matches):
        for w in self.basic_search_results_frame.winfo_children():
            w.destroy()
        if not matches:
            self._show_toast("No places matched. Use 'Enter Coordinates' to add custom village.")
            return
        self.basic_search_results_frame.pack(fill="x", padx=12, pady=6)
        tk.Label(
            self.basic_search_results_frame,
            text="Location Search Results (Click 'Add & Use' or 'Rename & Add'):",
            bg=UI_CARD_ALT, fg=UI_PURPLE_HOVER, font=("Segoe UI", 9, "bold"), anchor="w"
        ).pack(fill="x", padx=8, pady=(6, 4))

        for m in matches[:6]:
            r = tk.Frame(self.basic_search_results_frame, bg=UI_CARD_BG, padx=10, pady=6)
            r.pack(fill="x", padx=8, pady=2)
            tk.Label(
                r,
                text=f"{m['name']}  •  {m['source']} (Lat: {m['lat']:.4f}, Lon: {m['lon']:.4f})",
                bg=UI_CARD_BG, fg=UI_TEXT, font=("Segoe UI", 9), anchor="w"
            ).pack(side="left")
            tk.Button(
                r, text="Add & Use", bg=UI_PURPLE, fg=UI_TEXT, font=("Segoe UI", 8, "bold"),
                relief="flat", padx=10, pady=3, cursor="hand2",
                command=lambda item=m: self._add_search_result(item)
            ).pack(side="right", padx=(6, 0))
            tk.Button(
                r, text="Rename & Add", bg=UI_CARD_ALT, fg=UI_TEXT, font=("Segoe UI", 8, "bold"),
                relief="flat", padx=10, pady=3, cursor="hand2",
                command=lambda item=m: self._rename_search_result(item)
            ).pack(side="right")

    def _add_search_result(self, item):
        self.weather_locations.insert(0, {"name": item["name"], "lat": item["lat"], "lon": item["lon"]})
        self.weather_active_idx = 0
        save_weather_config(self.weather_locations, self.weather_active_idx, self.weather_units)
        self._build_basic_tab()
        self._on_weather_updated()
        self._show_toast(f"Activated '{item['name']}'")

    def _rename_search_result(self, item):
        self.manual_loc_expanded = True
        self._build_basic_tab()
        self.manual_name_var.set(self.basic_weather_search_var.get().strip() or item["name"])
        self.manual_lat_var.set(f"{item['lat']:.4f}")
        self.manual_lon_var.set(f"{item['lon']:.4f}")

    # =========================================================================
    # TAB 3: WIDGETS & POSITION (Exact Split Paned View Matching Linux)
    # =========================================================================
    def _build_widgets_tab(self):
        root_fr = self.tab_frames["widgets"]
        for w in root_fr.winfo_children():
            w.destroy()

        paned = tk.PanedWindow(root_fr, orient="horizontal", bg=UI_DIVIDER, sashwidth=2, bd=0)
        paned.pack(fill="both", expand=True)

        # LEFT SIDEBAR (Custom & Active Widgets + Save Suite + Apply Button)
        left_panel = tk.Frame(paned, bg=UI_BG, width=360, padx=14, pady=14)
        paned.add(left_panel, minsize=310)

        tk.Label(left_panel, text="Custom & Active Widgets", bg=UI_BG, fg=UI_TEXT, font=("Segoe UI", 11, "bold"), anchor="w").pack(fill="x")
        tk.Label(
            left_panel,
            text="Select any widget to drag its position on the monitor canvas, or save active widgets together as a new Suite.",
            bg=UI_BG, fg=UI_DIM, font=("Segoe UI", 8), anchor="w", justify="left", wraplength=330
        ).pack(fill="x", pady=(2, 8))

        list_scroll = ScrollableFrame(left_panel, bg=UI_CARD_BG)
        list_scroll.pack(fill="both", expand=True)
        list_scroll.configure(highlightthickness=1, highlightbackground=UI_BORDER)

        for idx, s in enumerate(self.skins):
            key = s["key"]
            st = self.skin_state[key]
            is_sel = key == self.selected_key
            row_bg = UI_SELECTED_ROW if is_sel else UI_CARD_BG

            row = tk.Frame(list_scroll.inner, bg=row_bg, padx=10, pady=8, cursor="hand2")
            row.pack(fill="x")

            txt_box = tk.Frame(row, bg=row_bg)
            txt_box.pack(side="left", fill="x", expand=True)
            t_lbl = tk.Label(txt_box, text=s["title"], bg=row_bg, fg=UI_TEXT, font=("Segoe UI", 10, "bold"), anchor="w")
            t_lbl.pack(fill="x")
            s_lbl = tk.Label(txt_box, text=f"{s['source']} • {s['subtitle']}", bg=row_bg, fg=UI_DIM, font=("Segoe UI", 8), anchor="w")
            s_lbl.pack(fill="x")

            for w_bind in (row, txt_box, t_lbl, s_lbl):
                w_bind.bind("<Button-1>", lambda _e, k=key: self._select_widget(k))

            PillSwitch(row, initial=st["active"], command=lambda val, k=key: self._set_widget_active(k, val), bg=row_bg).pack(side="left", padx=(6, 4))
            if not s["is_suite"]:
                tk.Button(
                    row, text="🗑", bg=row_bg, fg=UI_DIM, relief="flat", padx=4,
                    cursor="hand2", command=lambda sk=s: self._delete_custom_widget(sk)
                ).pack(side="left")

            if idx < len(self.skins) - 1:
                tk.Frame(list_scroll.inner, height=1, bg=UI_DIVIDER).pack(fill="x")

        # Create Suite from Active Widgets Card
        builder_card = tk.Frame(left_panel, bg=UI_CARD_BG, padx=10, pady=10, highlightthickness=1, highlightbackground=UI_BORDER)
        builder_card.pack(fill="x", pady=(10, 8))
        tk.Label(builder_card, text="Create Suite from Active Widgets", bg=UI_CARD_BG, fg=UI_TEXT, font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x", pady=(0, 6))
        brow = tk.Frame(builder_card, bg=UI_CARD_BG)
        brow.pack(fill="x")
        if not hasattr(self, "new_suite_var"):
            self.new_suite_var = tk.StringVar()
        tk.Entry(
            brow, textvariable=self.new_suite_var, bg=UI_CANVAS_BG, fg=UI_TEXT,
            insertbackground=UI_TEXT, relief="flat"
        ).pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 6))
        tk.Button(
            brow, text="Save Suite", bg=UI_PURPLE, fg=UI_TEXT, font=("Segoe UI", 9, "bold"),
            relief="flat", padx=12, pady=4, cursor="hand2", command=self._save_new_suite
        ).pack(side="right")

        tk.Button(
            left_panel, text="Apply Position & Reload Desktop", bg=UI_PURPLE, fg=UI_TEXT,
            font=("Segoe UI", 10, "bold"), relief="flat", pady=8, cursor="hand2",
            command=self._apply_and_reload
        ).pack(fill="x")

        # RIGHT SIDEBAR (Preview Canvas + Presets + Monitor/Scale + Position/Anchoring)
        right_scroll = ScrollableFrame(paned, bg=UI_BG)
        paned.add(right_scroll, minsize=520)

        right_box = tk.Frame(right_scroll.inner, bg=UI_BG, padx=18, pady=14)
        right_box.pack(fill="both", expand=True)

        sel_skin = next((s for s in self.skins if s["key"] == self.selected_key), self.skins[0] if self.skins else None)
        sel_title = sel_skin["title"] if sel_skin else "Select a Widget"
        sel_st = self.skin_state.get(self.selected_key, {}) if self.selected_key else {}

        tk.Label(right_box, text=sel_title, bg=UI_BG, fg=UI_TEXT, font=("Segoe UI", 15, "bold"), anchor="w").pack(fill="x", pady=(0, 10))

        # Interactive Desktop Positioner Canvas Card
        tk.Label(right_box, text="Interactive Desktop Positioner (Multi-Widget Preview)", bg=UI_BG, fg=UI_TEXT, font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
        tk.Label(
            right_box,
            text="Selected widget is shown in Cyan; other active widgets are shown in Purple. Click or drag any widget box on the canvas!",
            bg=UI_BG, fg=UI_DIM, font=("Segoe UI", 8), anchor="w"
        ).pack(fill="x", pady=(2, 6))

        self.pos_canvas = tk.Canvas(right_box, height=230, bg=UI_CANVAS_BG, highlightthickness=1, highlightbackground=UI_BORDER)
        self.pos_canvas.pack(fill="x")
        self.pos_canvas.bind("<ButtonPress-1>", self._on_canvas_drag_start)
        self.pos_canvas.bind("<B1-Motion>", self._on_canvas_drag_motion)
        self.pos_canvas.bind("<ButtonRelease-1>", self._on_canvas_drag_end)
        self.pos_canvas.bind("<Configure>", lambda _e: self._draw_monitor_preview())

        # 9-Button Anchor Presets Strip
        preset_bar = tk.Frame(right_box, bg=UI_BG)
        preset_bar.pack(pady=(8, 16))
        presets = [
            ("↖ Top-Left", "left", "top"), ("↑ Top-Center", "center", "top"), ("↗ Top-Right", "right", "top"),
            ("← Center-Left", "left", "center"), ("• Center", "center", "center"), ("→ Center-Right", "right", "center"),
            ("↙ Bottom-Left", "left", "bottom"), ("↓ Bottom-Center", "center", "bottom"), ("↘ Bottom-Right", "right", "bottom"),
        ]
        for lbl, ax, ay in presets:
            tk.Button(
                preset_bar, text=lbl, bg=UI_BG, fg=UI_TEXT, activebackground=UI_CARD_ALT,
                font=("Segoe UI", 8, "bold"), relief="flat", padx=6, pady=3,
                cursor="hand2", command=lambda x=ax, y=ay: self._set_quick_anchor(x, y)
            ).pack(side="left", padx=2)

        # Monitor and Screen Scaling Card
        scale_card = self._make_group(
            right_box,
            "Monitor and Screen Scaling",
            "Configure target monitor, automatic resolution fitting, or custom scale factor.",
        )
        _r, right, _lt, _ls = self._make_row(scale_card, "Target Monitor", "Display output where this widget is pinned (or choose All Monitors to show on both)")
        mon_names = self._get_monitor_dropdown_names()
        self.pos_mon_var = tk.StringVar(value=self._mon_val_to_dropdown_name(sel_st.get("monitor", 0)))
        pm_cb = ttk.Combobox(right, textvariable=self.pos_mon_var, values=mon_names, state="readonly", width=32)
        pm_cb.pack()
        pm_cb.bind("<<ComboboxSelected>>", self._on_pos_mon_changed)

        _r, right, _lt, _ls = self._make_row(scale_card, "Auto-Fit to Monitor Size", "Automatically scale widget proportionally to the target monitor resolution")
        PillSwitch(right, initial=sel_st.get("auto_fit", False), command=self._on_autofit_toggled).pack()

        _r, right, _lt, _ls = self._make_row(scale_card, "Manual Widget Scale", "Override scale factor when Auto-Fit is off (0.25× – 3.00×)", is_last=True)
        self.scale_var = tk.DoubleVar(value=sel_st.get("scale", 1.0))
        tk.Spinbox(
            right, from_=0.25, to=3.0, increment=0.05, textvariable=self.scale_var,
            width=7, bg=UI_CANVAS_BG, fg=UI_TEXT, buttonbackground=UI_CARD_ALT, relief="flat",
            command=self._on_manual_scale_changed
        ).pack(side="left", padx=(0, 6))
        tk.Button(
            right, text="1.0×", bg=UI_CARD_ALT, fg=UI_TEXT, relief="flat", padx=8, pady=2,
            cursor="hand2", command=lambda: self._set_manual_scale(1.0)
        ).pack(side="left")

        # Position and Anchoring Card
        pos_card = self._make_group(
            right_box,
            "Position and Anchoring",
            "Use automatic anchor alignment or exact pixel coordinates (WindowX, WindowY).",
        )
        _r, right, _lt, _ls = self._make_row(
            pos_card, "Use Custom Pixel Coordinates (WindowX / WindowY)", "Enable to pin at exact (X, Y) pixel offsets; disable to auto-align by Anchor"
        )
        PillSwitch(right, initial=sel_st.get("use_custom_pos", False), command=self._on_custom_pos_toggled).pack()

        _r, right, _lt, _ls = self._make_row(pos_card, "Pixel Offset (WindowX, WindowY)", "Relative to the top-left of the selected monitor", is_last=True)
        self.x_var = tk.IntVar(value=int(sel_st.get("x", 0)))
        self.y_var = tk.IntVar(value=int(sel_st.get("y", 0)))
        tk.Label(right, text="X:", bg=UI_CARD_BG, fg=UI_DIM).pack(side="left", padx=(0, 4))
        x_sp = tk.Spinbox(right, from_=-2000, to=8000, increment=5, textvariable=self.x_var, width=7, bg=UI_CANVAS_BG, fg=UI_TEXT, buttonbackground=UI_CARD_ALT, relief="flat", command=self._on_xy_spin_changed)
        x_sp.pack(side="left", padx=(0, 10))
        x_sp.bind("<Return>", lambda _e: self._on_xy_spin_changed())
        tk.Label(right, text="Y:", bg=UI_CARD_BG, fg=UI_DIM).pack(side="left", padx=(0, 4))
        y_sp = tk.Spinbox(right, from_=-2000, to=8000, increment=5, textvariable=self.y_var, width=7, bg=UI_CANVAS_BG, fg=UI_TEXT, buttonbackground=UI_CARD_ALT, relief="flat", command=self._on_xy_spin_changed)
        y_sp.pack(side="left")
        y_sp.bind("<Return>", lambda _e: self._on_xy_spin_changed())

        self._draw_monitor_preview()

    def _jump_to_positioner(self, key):
        self.selected_key = key
        self._build_widgets_tab()
        self._switch_tab("widgets")

    def _select_widget(self, key):
        self.selected_key = key
        self._build_widgets_tab()

    def _on_pos_mon_changed(self, _e=None):
        if not self.selected_key:
            return
        mon_val = self._dropdown_name_to_mon_val(self.pos_mon_var.get())
        self.skin_state[self.selected_key]["monitor"] = mon_val
        self.skin_state[self.selected_key]["monitors"] = list(range(len(self.monitors))) if mon_val == -1 else [mon_val]
        self._draw_monitor_preview()
        if self.skin_state[self.selected_key]["active"]:
            save_global_config(self.skins, self.skin_state, len(self.monitors))
            self.relaunch_desktop_widgets()

    def _on_autofit_toggled(self, val):
        if not self.selected_key:
            return
        self.skin_state[self.selected_key]["auto_fit"] = bool(val)
        self._draw_monitor_preview()
        if self.skin_state[self.selected_key]["active"]:
            save_global_config(self.skins, self.skin_state, len(self.monitors))
            self.relaunch_desktop_widgets()

    def _on_manual_scale_changed(self):
        if not self.selected_key:
            return
        try:
            self.skin_state[self.selected_key]["auto_fit"] = False
            self.skin_state[self.selected_key]["scale"] = max(0.25, min(3.0, float(self.scale_var.get())))
            self._draw_monitor_preview()
            if self.skin_state[self.selected_key]["active"]:
                save_global_config(self.skins, self.skin_state, len(self.monitors))
                self.relaunch_desktop_widgets()
        except Exception:
            pass

    def _set_manual_scale(self, val):
        self.scale_var.set(val)
        self._on_manual_scale_changed()

    def _on_custom_pos_toggled(self, val):
        if not self.selected_key:
            return
        self.skin_state[self.selected_key]["use_custom_pos"] = bool(val)
        self._draw_monitor_preview()

    def _on_xy_spin_changed(self):
        if not self.selected_key:
            return
        try:
            self.skin_state[self.selected_key]["use_custom_pos"] = True
            self.skin_state[self.selected_key]["x"] = int(self.x_var.get())
            self.skin_state[self.selected_key]["y"] = int(self.y_var.get())
            self._draw_monitor_preview()
        except Exception:
            pass

    def _set_quick_anchor(self, ax, ay):
        if not self.selected_key:
            return
        st = self.skin_state[self.selected_key]
        st["use_custom_pos"] = False
        st["anchor_x"] = ax
        st["anchor_y"] = ay
        save_global_config(self.skins, self.skin_state, len(self.monitors))
        self._build_widgets_tab()
        self.relaunch_desktop_widgets()

    def _get_preview_transform(self, cw, ch):
        raw_mon = self.skin_state.get(self.selected_key, {}).get("monitor", 0) if self.selected_key else 0
        mon_idx = 0 if raw_mon < 0 else min(raw_mon, len(self.monitors) - 1)
        mon = self.monitors[mon_idx]
        mw, mh = mon["width"], mon["height"]
        scale = min((cw - 40) / mw, (ch - 26) / mh)
        ox = (cw - mw * scale) / 2
        oy = (ch - mh * scale) / 2
        return scale, ox, oy, mw, mh

    def _draw_monitor_preview(self):
        if not hasattr(self, "pos_canvas") or not self.pos_canvas.winfo_exists():
            return
        c = self.pos_canvas
        c.delete("all")
        cw = max(500, c.winfo_width())
        ch = max(220, c.winfo_height())
        scale, ox, oy, mw, mh = self._get_preview_transform(cw, ch)
        raw_sel_mon = self.skin_state.get(self.selected_key, {}).get("monitor", 0) if self.selected_key else 0
        sel_mon = 0 if raw_sel_mon < 0 else min(raw_sel_mon, len(self.monitors) - 1)

        # Monitor outline & subtle grid crosshair
        c.create_rectangle(ox, oy, ox + mw * scale, oy + mh * scale, fill="#111722", outline="#385675", width=1.5)
        c.create_line(ox + (mw * scale) / 2, oy, ox + (mw * scale) / 2, oy + mh * scale, fill="#1E283A", dash=(2, 4))
        c.create_line(ox, oy + (mh * scale) / 2, ox + mw * scale, oy + (mh * scale) / 2, fill="#1E283A", dash=(2, 4))

        for s in self.skins:
            key = s["key"]
            st = self.skin_state[key]
            if not st["active"] and key != self.selected_key:
                continue
            act_mons = get_active_monitors_for_skin(st, len(self.monitors))
            if key != self.selected_key and sel_mon not in act_mons:
                continue
            eff_scale = compute_autofit_scale(s, mw, mh) if st.get("auto_fit", False) else st.get("scale", 1.0)
            w = int(s["est_w"] * eff_scale)
            h = int(s["est_h"] * eff_scale)
            if st["use_custom_pos"]:
                raw_x, raw_y = float(st["x"]), float(st["y"])
                if st.get("auto_fit", False):
                    ref_w = max(320, int(st.get("ref_w", 1366)))
                    ref_h = max(240, int(st.get("ref_h", 768)))
                    if mw != ref_w or mh != ref_h:
                        raw_x *= mw / float(ref_w)
                        raw_y *= mh / float(ref_h)
                x = max(0, min(mw - w, int(round(raw_x))))
                y = max(0, min(mh - h, int(round(raw_y))))
            else:
                x = (mw - w) // 2 if st["anchor_x"] == "center" else (mw - w if st["anchor_x"] == "right" else 0)
                y = (mh - h) // 2 if st["anchor_y"] == "center" else (mh - h if st["anchor_y"] == "bottom" else 0)
            rx1 = ox + x * scale
            ry1 = oy + y * scale
            rx2 = rx1 + max(42, w * scale)
            ry2 = ry1 + max(24, h * scale)
            is_sel = key == self.selected_key
            c.create_rectangle(
                rx1, ry1, rx2, ry2,
                fill="#163547" if is_sel else "#342254",
                outline=UI_CYAN if is_sel else "#8B5CF6",
                width=2 if is_sel else 1.4
            )
            c.create_text(
                rx1 + 6, (ry1 + ry2) / 2, anchor="w",
                text=f"{s['title']} ({int(x)}, {int(y)}) [{eff_scale:.2f}×]",
                fill=UI_TEXT, font=("Segoe UI", 8, "bold")
            )

    def _on_canvas_drag_start(self, event):
        if not self.selected_key:
            return
        cw = max(500, self.pos_canvas.winfo_width())
        ch = max(220, self.pos_canvas.winfo_height())
        scale, ox, oy, mw, mh = self._get_preview_transform(cw, ch)
        self._drag_origin = (event.x, event.y)
        st = self.skin_state[self.selected_key]
        if st["use_custom_pos"]:
            self._drag_win_start = (st["x"], st["y"])
        else:
            s = next((sk for sk in self.skins if sk["key"] == self.selected_key), None)
            w = int((s["est_w"] if s else 200) * st["scale"])
            h = int((s["est_h"] if s else 120) * st["scale"])
            ax = (mw - w) // 2 if st["anchor_x"] == "center" else (mw - w if st["anchor_x"] == "right" else 0)
            ay = (mh - h) // 2 if st["anchor_y"] == "center" else (mh - h if st["anchor_y"] == "bottom" else 0)
            self._drag_win_start = (ax, ay)

    def _on_canvas_drag_motion(self, event):
        if not self.selected_key or not hasattr(self, "_drag_origin"):
            return
        cw = max(500, self.pos_canvas.winfo_width())
        ch = max(220, self.pos_canvas.winfo_height())
        scale, _ox, _oy, mw, mh = self._get_preview_transform(cw, ch)
        dx = (event.x - self._drag_origin[0]) / max(0.05, scale)
        dy = (event.y - self._drag_origin[1]) / max(0.05, scale)
        s = next((sk for sk in self.skins if sk["key"] == self.selected_key), None)
        st = self.skin_state[self.selected_key]
        ew = int((s["est_w"] if s else 200) * st["scale"])
        eh = int((s["est_h"] if s else 120) * st["scale"])
        new_x = int(max(0, min(mw - min(mw, ew), self._drag_win_start[0] + dx)))
        new_y = int(max(0, min(mh - min(mh, eh), self._drag_win_start[1] + dy)))
        st["use_custom_pos"] = True
        st["x"] = new_x
        st["y"] = new_y
        st["ref_w"] = mw
        st["ref_h"] = mh
        self.x_var.set(new_x)
        self.y_var.set(new_y)
        self._draw_monitor_preview()

    def _on_canvas_drag_end(self, _event):
        save_global_config(self.skins, self.skin_state, len(self.monitors))
        self.relaunch_desktop_widgets()

    def _apply_and_reload(self):
        save_global_config(self.skins, self.skin_state, len(self.monitors))
        self.relaunch_desktop_widgets()
        self._show_toast("Applied positions & reloaded desktop widgets")

    def _save_new_suite(self):
        raw_name = self.new_suite_var.get().strip()
        if not raw_name:
            self._show_toast("Please enter a name for your new suite first")
            return
        folder_name = re.sub(r"[^A-Za-z0-9_-]+", "", raw_name.replace(" ", "_"))
        active_skins = [s for s in self.skins if self.skin_state[s["key"]]["active"]]
        if not active_skins:
            self._show_toast("Toggle at least one widget ON before saving a suite")
            return
        suite_dir = os.path.join(SUITES_DIR, folder_name)
        os.makedirs(suite_dir, exist_ok=True)
        payload = []
        for s in active_skins:
            st = self.skin_state[s["key"]]
            payload.append(
                {
                    "key": s["key"],
                    "title": s["title"],
                    "monitor": st["monitor"],
                    "anchor_x": st["anchor_x"],
                    "anchor_y": st["anchor_y"],
                    "use_custom_pos": st["use_custom_pos"],
                    "x": st["x"],
                    "y": st["y"],
                    "ref_width": int(st.get("ref_w", 1366)),
                    "ref_height": int(st.get("ref_h", 768)),
                    "auto_fit": st["auto_fit"],
                    "scale": st["scale"],
                }
            )
        with open(os.path.join(suite_dir, "suite.json"), "w", encoding="utf-8") as f:
            json.dump({"name": raw_name, "widgets": payload}, f, indent=2)
        self.custom_suites = discover_custom_suites()
        self.active_custom_suite_id = f"custom_suite::{folder_name}"
        self._build_suites_tab()
        self._show_toast(f"Saved suite '{raw_name}' ({len(active_skins)} widget(s)) to Suites tab!")

    def _delete_custom_widget(self, skin_info):
        key = skin_info["key"]
        widget_dir = os.path.dirname(skin_info["abs_path"])
        try:
            allowed = (os.path.abspath(USER_SKINS_DIR), os.path.abspath(WIDGETS_DIR))
            if os.path.isdir(widget_dir) and any(os.path.abspath(widget_dir).startswith(r + os.sep) for r in allowed):
                shutil.rmtree(widget_dir)
            elif os.path.isfile(skin_info["abs_path"]):
                os.remove(skin_info["abs_path"])
            self.skins = discover_all_skins()
            self.skin_state = load_global_config(self.skins)
            if self.selected_key == key:
                self.selected_key = self.skins[0]["key"] if self.skins else None
            self._build_basic_tab()
            self._build_widgets_tab()
            self.relaunch_desktop_widgets()
            self._show_toast(f"Removed '{skin_info['title']}'")
        except Exception as e:
            self._show_toast(f"Could not remove widget: {e}")

    # =========================================================================
    # ENGINE LIFECYCLE & TOP BAR ACTIONS
    # =========================================================================
    def relaunch_desktop_widgets(self):
        for w in self.active_desktop_windows:
            w.destroy()
        self.active_desktop_windows = []
        if not self.engine_running:
            return
        for s in self.skins:
            st = self.skin_state.get(s["key"])
            if st and st.get("active"):
                for m_idx in get_active_monitors_for_skin(st, len(self.monitors)):
                    win = DesktopWidgetWindow(self.root, s, st, self.monitors, self.telemetry, self.open_weather_popup, mon_idx=m_idx)
                    self.active_desktop_windows.append(win)

    def _on_toggle_power(self):
        self.engine_running = not self.engine_running
        if self.engine_running:
            self.power_btn.configure(text="Turn OFF", bg=UI_RED_BG, fg=UI_RED_FG)
            self.status_label.configure(text="● Running", fg=UI_GREEN_FG)
        else:
            self.power_btn.configure(text="Turn ON", bg="#1B4D3E", fg=UI_GREEN_FG)
            self.status_label.configure(text="○ Stopped", fg=UI_DIM)
        self.relaunch_desktop_widgets()

    def open_weather_popup(self):
        WeatherForecastPopupWindow(self.root, on_location_changed=self._on_weather_updated)

    def _on_weather_updated(self):
        self.telemetry.refresh_weather_async(force=True)
        for w in self.active_desktop_windows:
            w.redraw()

    def _on_open_skins_folder(self):
        os.makedirs(USER_SKINS_DIR, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(USER_SKINS_DIR)
            else:
                subprocess.Popen(["xdg-open", USER_SKINS_DIR])
        except Exception as e:
            self._show_toast(f"Skins folder: {USER_SKINS_DIR} ({e})")

    def _on_refresh_all(self):
        self.monitors = detect_monitors(self.root)
        self.skins = discover_all_skins()
        self.custom_suites = discover_custom_suites()
        self.skin_state = load_global_config(self.skins)
        self._build_suites_tab()
        self._build_basic_tab()
        self._build_widgets_tab()
        self.relaunch_desktop_widgets()
        self._show_toast("Reloaded skins & desktop layout")

    def _on_install_skin(self):
        path = filedialog.askopenfilename(
            title="Install Desktop Skin (.rmskin, .ini, or .zip)",
            filetypes=[("Desktop Widget Skins", "*.rmskin *.ini *.zip")],
        )
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        os.makedirs(USER_SKINS_DIR, exist_ok=True)
        try:
            if ext in (".rmskin", ".zip"):
                with zipfile.ZipFile(path, "r") as zf:
                    for member in zf.namelist():
                        norm = member.replace("\\", "/")
                        rel = norm[len("Skins/") :] if norm.startswith("Skins/") else norm
                        if not rel or rel.endswith("/") or rel.lower() in ("rmskin.ini", "rmskin.bmp"):
                            continue
                        dest = os.path.join(USER_SKINS_DIR, rel)
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        with zf.open(member) as src, open(dest, "wb") as dst:
                            shutil.copyfileobj(src, dst)
            elif ext == ".ini":
                stem = os.path.splitext(os.path.basename(path))[0]
                dest_dir = os.path.join(USER_SKINS_DIR, stem)
                os.makedirs(dest_dir, exist_ok=True)
                shutil.copy2(path, os.path.join(dest_dir, os.path.basename(path)))
            self.skins = discover_all_skins()
            self.skin_state = load_global_config(self.skins)
            self._build_suites_tab()
            self._build_basic_tab()
            self._build_widgets_tab()
            self._show_toast(f"Installed skin: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Install Failed", str(e))

    def _on_export_rmskin(self):
        if build_rmskin_package is None:
            messagebox.showerror("Export .rmskin", "build_rmskin module not found.")
            return
        save_to = filedialog.asksaveasfilename(
            title="Export Windows Rainmeter .rmskin Package",
            defaultextension=".rmskin",
            initialfile="TradDesktop_1.2.0.rmskin",
            filetypes=[("Rainmeter Skin Package", "*.rmskin")],
        )
        if not save_to:
            return
        try:
            out = build_rmskin_package(output_path=save_to, version="1.2.0", config_dir=CONFIG_DIR)
            messagebox.showinfo(
                "Export Complete",
                f"Exported Windows Rainmeter package:\n{out}\n\nDouble-click this .rmskin file on Windows to install all Trad Suites & Widgets into classic Rainmeter!",
            )
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def _schedule_tick(self):
        self.telemetry.update_telemetry()
        for w in self.active_desktop_windows:
            w.redraw()
        self.root.after(1000, self._schedule_tick)


def main():
    root = tk.Tk()
    if "--weather-popup" in sys.argv:
        root.withdraw()
        popup = WeatherForecastPopupWindow(root)
        popup.win.protocol("WM_DELETE_WINDOW", root.destroy)
        root.mainloop()
        return
    TradDesktopWindowsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

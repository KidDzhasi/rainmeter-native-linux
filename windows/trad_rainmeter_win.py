#!/usr/bin/env python3
"""
Trad Rainmeter for Windows — Standalone Desktop Widget Engine & Control Center
Runs natively on Windows 10 / 11 (and cross-platform for testing on Linux):
  • Standalone Desktop Widget Engine: Renders Trad Suites (TradSunset, Trad Cyber,
    DashboardSuite, GreenRibbonSuite), 8 Basic Widgets, 3 Music Players, 2 Audio
    Visualizers, and custom .rmskin/.ini skins directly pinned to the Windows desktop
    wallpaper layer (HWND_BOTTOM, WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE, non-draggable).
  • 3-Tab Control Center GUI:
      1. Suites: One-click suite switching & monitor AutoFit
      2. Basic Widgets: 10 Color Themes, 6 Card Shapes, 4 Gauge Designs, Music Players,
         Audio Visualizers, and Live Weather + Rural Village Search (ArcGIS + Open-Meteo
         + met.no fallback)
      3. Widgets & Position: Interactive Multi-Widget Monitor Canvas, .rmskin/.ini
         Installer, Custom Suite Builder, and 1-Click .rmskin Exporter for classic
         Windows Rainmeter.
  • Clickable 24-Hour & 7-Day Weather Forecast Popup (--weather-popup).
"""

import concurrent.futures
import configparser
import ctypes
import datetime
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import urllib.parse
import urllib.request
import zipfile

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
    CONFIG_DIR = os.path.join(APPDATA_BASE, "TradRainmeter")
    CACHE_DIR = os.path.join(LOCALAPPDATA_BASE, "TradRainmeter", "cache")
else:
    CONFIG_DIR = os.path.expanduser("~/.config/rainmeter-native")
    CACHE_DIR = os.path.expanduser("~/.cache/trad-rainmeter")

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

# Optional psutil for enhanced Windows telemetry (falls back to Win32 ctypes if absent)
try:
    import psutil
except ImportError:
    psutil = None

# ---------------------------------------------------------------------------
# Theme, Shape & Design Catalog (Identical to Linux Trad Rainmeter)
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
        "border_hex": "#556070",
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
        "subtitle": "Light airy frosted crystal glass with bright aqua-blue glow",
        "corner_radius": 12,
        "bg_fill": "Fill LinearGradient 135 | 60,90,125,135 | 30,50,75,155",
        "border_stroke": "StrokeWidth 1.5 | Stroke Color 180,235,255,150",
        "accent": "64,224,208,255",
        "text": "255,255,255,255",
        "bg_hex": "#3C5A7D",
        "border_hex": "#B4EBFF",
        "accent_hex": "#40E0D0",
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
    {"id": "rounded", "name": "Rounded Card (Default)", "radius": None, "borderless": False},
    {"id": "sharp", "name": "Sharp Rectangular Box", "radius": 0, "borderless": False},
    {"id": "squircle", "name": "Soft Squircle (20px)", "radius": 20, "borderless": False},
    {"id": "pill", "name": "Full Pill / Capsule (36px)", "radius": 36, "borderless": False},
    {"id": "circle", "name": "Circular / Oval Disc (80px)", "radius": 80, "borderless": False},
    {"id": "floating", "name": "Floating Borderless (No Card)", "radius": 0, "borderless": True},
]

BASIC_WIDGET_DESIGNS = [
    {"id": "bars", "name": "Vertical Telemetry Bars (Classic)"},
    {"id": "circular", "name": "Circular Ring Gauges (Arc Dial)"},
    {"id": "pill", "name": "Compact Capsule Pill (Horizontal Bar)"},
    {"id": "minimal", "name": "Horizontal Minimal Typography"},
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
        "; Auto-generated by Trad Rainmeter Weather Location Manager\n"
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
    code = int(code)
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
    return mapping.get(code, "Partly Cloudy")


def deg_to_cardinal(deg):
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = int(((float(deg) + 11.25) % 360.0) / 22.5) % 16
    return dirs[idx]


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
    if "Cloud" in s or "cloudy" in s:
        return 2 if "partly" in s else 3
    if "fair" in s:
        return 1
    return 0


def _fetch_forecast_from_met_no(lat, lon, units="metric"):
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={float(lat):.4f}&lon={float(lon):.4f}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "TradRainmeter/1.1 (https://github.com/KidDzhasi/Trad-rainmeter)",
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
        "hourly": {
            "time": h_times,
            "temperature_2m": h_temps,
            "precipitation_probability": h_pops,
            "weather_code": h_codes,
        },
        "daily": {
            "time": d_times,
            "weather_code": d_codes,
            "temperature_2m_max": d_max,
            "temperature_2m_min": d_min,
            "precipitation_probability_max": d_pop,
        },
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
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "TradRainmeter/1.1", "Accept": "application/json"},
    )
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
    """Multi-source village & city geocoder (ArcGIS World Geocoder + Open-Meteo + Nominatim)."""
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
        req = urllib.request.Request(url, headers={"User-Agent": "TradRainmeter/1.1"})
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
        req = urllib.request.Request(url, headers={"User-Agent": "TradRainmeter/1.1"})
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
# System Telemetry & Media Backend for Windows (and cross-platform fallback)
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
            # Pure Win32 ctypes fallback when psutil is not installed
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

        # Update audio spectrum bars smoothly
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
            VK_MEDIA_NEXT_TRACK = 0xB0
            VK_MEDIA_PREV_TRACK = 0xB1
            VK_MEDIA_PLAY_PAUSE = 0xB3
            vk = VK_MEDIA_PLAY_PAUSE
            if "next" in c:
                vk = VK_MEDIA_NEXT_TRACK
            elif "prev" in c:
                vk = VK_MEDIA_PREV_TRACK
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
# Theme & Design Writers (Shared with Linux Control Center)
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
        "; Auto-generated by Trad Rainmeter Theme, Shape & Design Studio\n"
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


# ---------------------------------------------------------------------------
# Skin Discovery & Configuration Persistence
# ---------------------------------------------------------------------------
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
                                "title": folder,
                                "subtitle": rel_key,
                                "abs_path": abs_p,
                                "is_suite": True,
                                "is_basic": False,
                                "source": "Desktop Suite",
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
                        items.append(
                            {
                                "key": rel_key,
                                "title": folder,
                                "subtitle": f"Anchored ({meta['anchor_x'].capitalize()}-{meta['anchor_y'].capitalize()}) • {meta['width']}×{meta['height']}",
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
    for base in dict.fromkeys([SYSTEM_SUITES_DIR, SUITES_DIR]):
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
            "anchor_x": s["default_anchor_x"],
            "anchor_y": s["default_anchor_y"],
            "use_custom_pos": has_def_xy,
            "x": s["default_x"] if has_def_xy else 0,
            "y": s["default_y"] if has_def_xy else 0,
            "auto_fit": s["is_suite"],
            "scale": 1.0,
        }
    if not os.path.isfile(GLOBAL_CONFIG):
        for s in skins:
            if "TradSunset" in s["key"]:
                state[s["key"]]["active"] = True
                break
        return state

    cp = configparser.ConfigParser(interpolation=None, strict=False)
    cp.optionxform = str
    try:
        with open(GLOBAL_CONFIG, "r", encoding="utf-8", errors="ignore") as f:
            cp.read_file(f)
        for sec in cp.sections():
            norm_sec = sec.replace("\\", "/")
            matched_key = next(
                (s["key"] for s in skins if norm_sec == s["key"] or s["abs_path"].replace("\\", "/").endswith(norm_sec)),
                None,
            )
            if not matched_key:
                continue
            st = state[matched_key]
            sec_map = {k.lower(): v.strip() for k, v in cp.items(sec)}
            st["active"] = sec_map.get("active", "0") not in ("0", "false", "")
            if "anchorx" in sec_map:
                st["anchor_x"] = sec_map["anchorx"].lower()
            if "anchory" in sec_map:
                st["anchor_y"] = sec_map["anchory"].lower()
            if "autofit" in sec_map:
                st["auto_fit"] = sec_map["autofit"].lower() in ("1", "true", "yes")
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


def save_global_config(skins, state):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    lines = ["; Rainmeter Native Global Configuration\n"]
    for s in skins:
        key = s["key"]
        st = state.get(key)
        if not st:
            continue
        lines.append(f"[{key}]\n")
        lines.append(f"Active={1 if st['active'] else 0}\n")
        lines.append(f"Monitor={st['monitor']}\n")
        lines.append(f"AnchorX={st['anchor_x'].capitalize()}\n")
        lines.append(f"AnchorY={st['anchor_y'].capitalize()}\n")
        lines.append(f"AutoFit={1 if st['auto_fit'] else 0}\n")
        if st["use_custom_pos"]:
            lines.append(f"WindowX={int(st['x'])}\n")
            lines.append(f"WindowY={int(st['y'])}\n")
        lines.append("\n")
    with open(GLOBAL_CONFIG, "w", encoding="utf-8") as f:
        f.writelines(lines)


# ---------------------------------------------------------------------------
# Pinned Desktop Widget Renderer Window (Win32 HWND_BOTTOM Desktop Overlay)
# ---------------------------------------------------------------------------
class DesktopWidgetWindow:
    """
    Renders an active Trad Rainmeter suite or widget pinned to the Windows desktop
    background (borderless, non-draggable, click-responsive for Weather & Music).
    """

    def __init__(self, master, skin_info, skin_state, telemetry, on_open_weather):
        self.master = master
        self.skin_info = skin_info
        self.state = skin_state
        self.telemetry = telemetry
        self.on_open_weather = on_open_weather

        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)

        # Compute pinned screen position
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        w = min(sw, max(130, skin_info["est_w"]))
        h = min(sh, max(70, skin_info["est_h"]))
        if skin_info["is_suite"]:
            w, h = min(sw, 920), min(sh, 520)

        if skin_state.get("use_custom_pos"):
            x = max(0, min(sw - w, int(skin_state.get("x", 40))))
            y = max(0, min(sh - h, int(skin_state.get("y", 40))))
        else:
            ax = skin_state.get("anchor_x", "center")
            ay = skin_state.get("anchor_y", "center")
            x = (sw - w) // 2 if ax == "center" else (sw - w - 24 if ax == "right" else 24)
            y = (sh - h) // 2 if ay == "center" else (sh - h - 48 if ay == "bottom" else 36)

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
        """Pin window to the Windows desktop bottom Z-order and hide from Alt+Tab / Taskbar."""
        if sys.platform == "win32":
            try:
                self.win.update_idletasks()
                hwnd = ctypes.windll.user32.GetParent(self.win.winfo_id()) or self.win.winfo_id()
                GWL_EXSTYLE = -20
                WS_EX_TOOLWINDOW = 0x00000080
                WS_EX_NOACTIVATE = 0x08000000
                style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                ctypes.windll.user32.SetWindowLongW(
                    hwnd, GWL_EXSTYLE, style | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
                )
                HWND_BOTTOM = 1
                SWP_NOACTIVATE = 0x0010
                ctypes.windll.user32.SetWindowPos(
                    hwnd,
                    HWND_BOTTOM,
                    self.pinned_x,
                    self.pinned_y,
                    self.width,
                    self.height,
                    SWP_NOACTIVATE,
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
        if "weather" in title or self.skin_info["is_suite"]:
            if not self.skin_info["is_suite"] or event.x > self.width * 0.6:
                self.on_open_weather()
                return
        if "music" in title or self.skin_info["is_suite"]:
            # Check prev / play-pause / next zones
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
            # Render Full-Screen Desktop Suite (Clock + Date + CPU/Disk Rings + Music + Weather + Visualizer)
            cx, cy = self.width // 2, self.height // 2
            day_spaced = "  ".join(list(now.strftime("%A").upper()))
            c.create_text(cx, cy - 35, text=day_spaced, fill="#FFFFFF", font=("Segoe UI", 28, "bold"))
            c.create_text(
                cx,
                cy + 14,
                text=now.strftime("%d  %b  %Y").upper(),
                fill="#E2E8F0",
                font=("Segoe UI", 12, "bold"),
            )
            c.create_text(
                cx,
                cy + 40,
                text=now.strftime("-  %I : %M  %p  -"),
                fill=ac_hex,
                font=("Segoe UI", 12, "bold"),
            )

            # Top-right circular gauges (Disk & CPU)
            for idx_g, (label, pct, gx) in enumerate(
                [("DISK", self.telemetry.disk_percent, self.width - 185), ("CPU", self.telemetry.cpu_percent, self.width - 80)]
            ):
                gy = 62
                c.create_oval(gx - 36, gy - 36, gx + 36, gy + 36, outline="#2A324B", width=6)
                extent = -max(5.0, min(359.0, (pct / 100.0) * 360.0))
                c.create_arc(
                    gx - 36,
                    gy - 36,
                    gx + 36,
                    gy + 36,
                    start=90,
                    extent=extent,
                    style="arc",
                    outline="#FFB703" if "Sunset" in title else ac_hex,
                    width=6,
                )
                c.create_text(gx, gy - 6, text=f"{pct:.1f}%", fill="#FFFFFF", font=("Segoe UI", 10, "bold"))
                c.create_text(gx, gy + 12, text=label, fill="#94A3B8", font=("Segoe UI", 8, "bold"))

            # Media Player block
            mx, my = self.width - 230, 155
            c.create_text(mx, my, anchor="w", text=self.telemetry.media_title, fill="#FFFFFF", font=("Segoe UI", 10, "bold"))
            c.create_text(mx, my + 18, anchor="w", text=self.telemetry.media_artist, fill="#94A3B8", font=("Segoe UI", 8))
            play_sym = "⏸" if self.telemetry.media_playing else "▶"
            c.create_text(self.width - 55, my + 8, text=f"⏮   {play_sym}   ⏭", fill="#FFB703", font=("Segoe UI", 12, "bold"))

            # Clickable Live Weather block
            wx, wy = self.width - 230, 235
            c.create_text(wx, wy, anchor="w", text=w_data["Location"], fill="#FFB703", font=("Segoe UI", 10, "bold"))
            c.create_text(wx, wy + 18, anchor="w", text=f"Currently - {w_data['Condition']}", fill="#FFFFFF", font=("Segoe UI", 9))
            c.create_text(wx, wy + 38, anchor="w", text=f"H {w_data['High']}  L {w_data['Low']}  Feels {w_data['FeelsLike']}", fill="#94A3B8", font=("Segoe UI", 8))
            c.create_text(self.width - 30, wy + 28, anchor="e", text=w_data["Temp"], fill="#FFFFFF", font=("Segoe UI", 22, "bold"))
            c.create_text(wx, wy + 60, anchor="w", text=f"Humidity: {w_data['Humidity']}%  •  Rain: {w_data['RainProb']}%", fill="#94A3B8", font=("Segoe UI", 8))
            c.create_text(wx, wy + 76, anchor="w", text=f"Wind: {w_data['WindSpeed']} - {w_data['WindDir']}  ({w_data['Updated']})", fill="#94A3B8", font=("Segoe UI", 8))

            # Bottom-right 20-band Audio Visualizer
            vx, vy = self.width - 240, self.height - 22
            for b_idx, amp in enumerate(self.telemetry.fft_bands):
                bh = max(4, int(amp * 75))
                bx = vx + b_idx * 11
                c.create_rectangle(bx, vy - bh, bx + 8, vy, fill="#FFB703" if "Sunset" in title else ac_hex, outline="")
            return

        # Modular Basic Widget card background
        if not shape.get("borderless", False):
            c.create_rectangle(
                3,
                3,
                self.width - 3,
                self.height - 3,
                fill=bg_hex,
                outline=bd_hex,
                width=2,
            )

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
            c.create_arc(
                gx - 24,
                gy - 24,
                gx + 24,
                gy + 24,
                start=90,
                extent=-max(6.0, min(359.0, (pct / 100.0) * 360.0)),
                style="arc",
                outline=ac_hex,
                width=5,
            )
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
        self.win.title("Trad Rainmeter — Live Weather Forecast & Villages")
        self.win.geometry("860x620")
        self.win.configure(bg="#171520")

        ico_path = os.path.join(REPO_DIR, "assets", "trad-engine.ico")
        if sys.platform == "win32" and os.path.isfile(ico_path):
            try:
                self.win.iconbitmap(ico_path)
            except Exception:
                pass

        self.locations, self.active_idx, self.units = load_weather_config()
        self.forecast_data = None

        # Top Toolbar
        top = tk.Frame(self.win, bg="#1F1C2C", padx=14, pady=10)
        top.pack(fill="x")

        tk.Label(top, text="Location:", bg="#1F1C2C", fg="#CBD5E1", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.loc_var = tk.StringVar(value=self.locations[self.active_idx]["name"])
        self.loc_combo = ttk.Combobox(
            top,
            textvariable=self.loc_var,
            values=[l["name"] for l in self.locations],
            state="readonly",
            width=32,
        )
        self.loc_combo.pack(side="left", padx=8)
        self.loc_combo.bind("<<ComboboxSelected>>", self._on_loc_selected)

        tk.Button(
            top,
            text="↻ Refresh",
            bg="#312E43",
            fg="#FFFFFF",
            relief="flat",
            padx=10,
            command=lambda: self.refresh_forecast(force=True),
        ).pack(side="left", padx=4)

        # Search Village / City inline bar
        tk.Label(top, text="Search Village / City:", bg="#1F1C2C", fg="#CBD5E1", font=("Segoe UI", 9)).pack(side="left", padx=(16, 4))
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(top, textvariable=self.search_var, bg="#2A263B", fg="#FFFFFF", insertbackground="#FFFFFF", width=22)
        search_entry.pack(side="left", padx=4)
        search_entry.bind("<Return>", lambda _e: self._on_search())
        tk.Button(
            top,
            text="Search & Add",
            bg="#7C3AED",
            fg="#FFFFFF",
            relief="flat",
            padx=10,
            command=self._on_search,
        ).pack(side="left", padx=4)

        # Search Results Bar (hidden until search)
        self.search_frame = tk.Frame(self.win, bg="#231F32", padx=14, pady=6)

        # Current Weather Hero Card
        hero = tk.Frame(self.win, bg="#211E2F", padx=18, pady=14)
        hero.pack(fill="x", padx=16, pady=(12, 8))

        self.lbl_place = tk.Label(hero, text="Loading...", bg="#211E2F", fg="#FFFFFF", font=("Segoe UI", 16, "bold"))
        self.lbl_place.pack(anchor="w")
        self.lbl_temp = tk.Label(hero, text="--°", bg="#211E2F", fg="#FFB703", font=("Segoe UI", 28, "bold"))
        self.lbl_temp.pack(anchor="w")
        self.lbl_details = tk.Label(hero, text="Fetching forecast...", bg="#211E2F", fg="#CBD5E1", font=("Segoe UI", 10))
        self.lbl_details.pack(anchor="w")

        # 24-Hour Temperature Curve Canvas
        tk.Label(
            self.win,
            text="Hourly Forecast (Next 24 Hours — Temperature Curve & Rain Chance)",
            bg="#171520",
            fg="#E2E8F0",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=18)

        self.curve_canvas = tk.Canvas(self.win, height=185, bg="#1E1B2B", highlightthickness=1, highlightbackground="#312E43")
        self.curve_canvas.pack(fill="x", padx=16, pady=6)
        self.curve_canvas.bind("<Configure>", lambda _e: self._draw_hourly_curve())

        # 7-Day Forecast List
        tk.Label(
            self.win,
            text="7-Day Forecast",
            bg="#171520",
            fg="#E2E8F0",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=18, pady=(6, 2))

        self.daily_frame = tk.Frame(self.win, bg="#211E2F", padx=14, pady=8)
        self.daily_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self.daily_labels = []
        for _ in range(7):
            row = tk.Frame(self.daily_frame, bg="#211E2F")
            row.pack(fill="x", pady=2)
            l_day = tk.Label(row, text="--", bg="#211E2F", fg="#FFFFFF", font=("Segoe UI", 10, "bold"), width=22, anchor="w")
            l_day.pack(side="left")
            l_cond = tk.Label(row, text="--", bg="#211E2F", fg="#94A3B8", font=("Segoe UI", 9), width=32, anchor="w")
            l_cond.pack(side="left")
            l_range = tk.Label(row, text="--", bg="#211E2F", fg="#FFB703", font=("Segoe UI", 10, "bold"), anchor="e")
            l_range.pack(side="right")
            self.daily_labels.append((l_day, l_cond, l_range))

        self.refresh_forecast(force=False)

    def _on_loc_selected(self, _event=None):
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
        self.lbl_details.configure(text=f"Searching for '{q}' across ArcGIS World Geocoder & Open-Meteo...")

        def _worker():
            matches = search_village_or_city(q)
            self.win.after(0, lambda: self._show_search_results(matches))

        threading.Thread(target=_worker, daemon=True).start()

    def _show_search_results(self, matches):
        for w in self.search_frame.winfo_children():
            w.destroy()
        if not matches:
            self.lbl_details.configure(text="No matching village or city found. Try entering 'lat, lon' coordinates.")
            return
        self.search_frame.pack(fill="x", padx=16, pady=4, before=self.curve_canvas)
        tk.Label(self.search_frame, text="Click a result to add & activate:", bg="#231F32", fg="#A78BFA", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        for m in matches[:5]:
            btn = tk.Button(
                self.search_frame,
                text=f"＋ {m['name']}  ({m['lat']:.4f}, {m['lon']:.4f} • {m['source']})",
                bg="#2E2942",
                fg="#FFFFFF",
                relief="flat",
                anchor="w",
                padx=8,
                pady=2,
                command=lambda item=m: self._add_and_use_location(item),
            )
            btn.pack(fill="x", pady=1)

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
        self.lbl_details.configure(
            text=f"Humidity: {hum}%   •   Rain Chance: {pop}%   •   Wind: {wind} {w_sym} ({wdir})   •   ({loc['lat']:.4f}, {loc['lon']:.4f})"
        )
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
            py = 58 + (1.0 - (tv - t_min) / t_span) * (h - 92)
            pts.append((px, py))
            t_lbl = "Now" if i == 0 else (times[i].split("T")[-1][:5] if i < len(times) else "")
            c.create_text(px, 16, text=t_lbl, fill="#CBD5E1", font=("Segoe UI", 8))
            if i < len(pops):
                c.create_text(px, 32, text=f"{pops[i]}%", fill="#38BDF8", font=("Segoe UI", 8, "bold"))
            c.create_text(px, h - 14, text=f"{round(tv)}°", fill="#FFB703", font=("Segoe UI", 9, "bold"))

        for i in range(len(pts) - 1):
            c.create_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], fill="#FFB703", width=3)
        for px, py in pts:
            c.create_oval(px - 3, py - 3, px + 3, py + 3, fill="#FFB703", outline="#FFFFFF")


# ---------------------------------------------------------------------------
# Trad Rainmeter Windows Control Center (3 Tabs + Live Desktop Widget Host)
# ---------------------------------------------------------------------------
class TradRainmeterWindowsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Trad Rainmeter — Windows Control Center")
        self.root.geometry("1060x760")
        self.root.configure(bg="#13111C")

        ico_path = os.path.join(REPO_DIR, "assets", "trad-engine.ico")
        if sys.platform == "win32" and os.path.isfile(ico_path):
            try:
                self.root.iconbitmap(ico_path)
            except Exception:
                pass

        self.telemetry = SystemTelemetryBackend()
        self.skins = discover_all_skins()
        self.custom_suites = discover_custom_suites()
        self.skin_state = load_global_config(self.skins)
        self.basic_theme_idx, self.basic_shape_idx, self.basic_design_idx = read_current_basic_style()
        self.weather_locations, self.weather_active_idx, self.weather_units = load_weather_config()
        save_weather_config(self.weather_locations, self.weather_active_idx, self.weather_units)

        self.active_desktop_windows = []
        self.engine_running = True
        self.selected_key = next((s["key"] for s in self.skins if not s["is_suite"]), self.skins[0]["key"] if self.skins else None)

        self._configure_dark_style()
        self._build_ui()
        self.relaunch_desktop_widgets()
        self._schedule_tick()

    def _configure_dark_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TNotebook", background="#13111C", borderwidth=0)
        style.configure("TNotebook.Tab", background="#1F1C2C", foreground="#CBD5E1", padding=(16, 8), font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "#7C3AED")], foreground=[("selected", "#FFFFFF")])
        style.configure("TFrame", background="#13111C")
        style.configure("Card.TFrame", background="#1E1B2B")

    def _build_ui(self):
        # Header Bar
        header = tk.Frame(self.root, bg="#1B1828", padx=16, pady=10)
        header.pack(fill="x")

        tk.Button(
            header,
            text="＋ Install .rmskin / .ini…",
            bg="#7C3AED",
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=12,
            pady=5,
            command=self._on_install_skin,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            header,
            text="📦 Export .rmskin for Windows Rainmeter",
            bg="#2563EB",
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=12,
            pady=5,
            command=self._on_export_rmskin,
        ).pack(side="left", padx=4)

        tk.Button(
            header,
            text="☁ Weather Forecast & Villages",
            bg="#2D283E",
            fg="#FFB703",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=12,
            pady=5,
            command=self.open_weather_popup,
        ).pack(side="left", padx=4)

        self.power_btn = tk.Button(
            header,
            text="Turn OFF Widgets",
            bg="#DC2626",
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=14,
            pady=5,
            command=self._on_toggle_power,
        )
        self.power_btn.pack(side="right")

        self.status_lbl = tk.Label(
            header,
            text="● Desktop Widgets Active (Pinned)",
            bg="#1B1828",
            fg="#34D399",
            font=("Segoe UI", 9, "bold"),
        )
        self.status_lbl.pack(side="right", padx=12)

        # 3-Tab Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=8)

        self.tab_suites = ttk.Frame(self.notebook)
        self.tab_basic = ttk.Frame(self.notebook)
        self.tab_position = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_suites, text="  🖼  Suites  ")
        self.notebook.add(self.tab_basic, text="  ⊞  Basic Widgets & Weather  ")
        self.notebook.add(self.tab_position, text="  ✥  Widgets & Position  ")

        self._build_suites_tab()
        self._build_basic_tab()
        self._build_position_tab()

    # --- TAB 1: SUITES ---
    def _build_suites_tab(self):
        for w in self.tab_suites.winfo_children():
            w.destroy()
        container = tk.Frame(self.tab_suites, bg="#13111C", padx=20, pady=16)
        container.pack(fill="both", expand=True)

        tk.Label(
            container,
            text="One-Click Desktop Suites (Pinned & Auto-Fitted to Monitor)",
            bg="#13111C",
            fg="#FFFFFF",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w")
        tk.Label(
            container,
            text="Activating a suite automatically replaces any previous active widgets and pins the suite cleanly to your Windows desktop.",
            bg="#13111C",
            fg="#94A3B8",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(2, 12))

        for s in [sk for sk in self.skins if sk["is_suite"]]:
            is_act = self.skin_state[s["key"]]["active"]
            card = tk.Frame(container, bg="#1E1B2B", padx=16, pady=12, highlightthickness=1, highlightbackground="#7C3AED" if is_act else "#2E2942")
            card.pack(fill="x", pady=5)
            tk.Label(card, text=s["title"], bg="#1E1B2B", fg="#FFFFFF", font=("Segoe UI", 11, "bold")).pack(side="left")
            tk.Label(card, text=f"   ({s['subtitle']} • {s['est_w']}×{s['est_h']})", bg="#1E1B2B", fg="#94A3B8", font=("Segoe UI", 9)).pack(side="left")
            tk.Button(
                card,
                text="Active ✓" if is_act else "Apply Suite",
                bg="#10B981" if is_act else "#7C3AED",
                fg="#FFFFFF",
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                padx=14,
                pady=4,
                command=lambda k=s["key"]: self._activate_suite(k),
            ).pack(side="right")

        for cs in self.custom_suites:
            card = tk.Frame(container, bg="#1E1B2B", padx=16, pady=12, highlightthickness=1, highlightbackground="#2E2942")
            card.pack(fill="x", pady=5)
            tk.Label(card, text=f"{cs['title']} (Saved Custom Suite)", bg="#1E1B2B", fg="#A78BFA", font=("Segoe UI", 11, "bold")).pack(side="left")
            tk.Label(card, text=f"   • {len(cs['widgets'])} widgets", bg="#1E1B2B", fg="#94A3B8", font=("Segoe UI", 9)).pack(side="left")
            tk.Button(
                card,
                text="Apply Custom Suite",
                bg="#7C3AED",
                fg="#FFFFFF",
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                padx=14,
                pady=4,
                command=lambda item=cs: self._activate_custom_suite(item),
            ).pack(side="right")

    def _activate_suite(self, suite_key):
        for s in self.skins:
            is_t = s["key"] == suite_key
            self.skin_state[s["key"]]["active"] = is_t
            if is_t:
                self.skin_state[s["key"]]["use_custom_pos"] = False
                self.skin_state[s["key"]]["anchor_x"] = "center"
                self.skin_state[s["key"]]["anchor_y"] = "center"
        save_global_config(self.skins, self.skin_state)
        self._build_suites_tab()
        self._build_basic_tab()
        self.relaunch_desktop_widgets()

    def _activate_custom_suite(self, cs):
        for s in self.skins:
            self.skin_state[s["key"]]["active"] = False
        for w in cs["widgets"]:
            wkey = w.get("key", "")
            matched = next((s["key"] for s in self.skins if s["key"] == wkey or s["key"].endswith(os.path.basename(wkey))), None)
            if matched:
                st = self.skin_state[matched]
                st["active"] = True
                st["use_custom_pos"] = w.get("use_custom_pos", False)
                st["x"] = w.get("x", 0)
                st["y"] = w.get("y", 0)
        save_global_config(self.skins, self.skin_state)
        self._build_suites_tab()
        self._build_basic_tab()
        self.relaunch_desktop_widgets()

    # --- TAB 2: BASIC WIDGETS, THEME STUDIO & WEATHER ---
    def _build_basic_tab(self):
        for w in self.tab_basic.winfo_children():
            w.destroy()

        outer = tk.Frame(self.tab_basic, bg="#13111C", padx=18, pady=12)
        outer.pack(fill="both", expand=True)

        # Style selectors (Theme, Shape, Design)
        style_card = tk.Frame(outer, bg="#1E1B2B", padx=16, pady=12)
        style_card.pack(fill="x", pady=(0, 10))

        tk.Label(style_card, text="Theme, Shape & Gauge Design Studio", bg="#1E1B2B", fg="#FFFFFF", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 8))

        tk.Label(style_card, text="Color Theme:", bg="#1E1B2B", fg="#CBD5E1").grid(row=1, column=0, sticky="w")
        self.theme_var = tk.StringVar(value=BASIC_WIDGET_THEMES[self.basic_theme_idx]["name"])
        theme_cb = ttk.Combobox(style_card, textvariable=self.theme_var, values=[t["name"] for t in BASIC_WIDGET_THEMES], state="readonly", width=26)
        theme_cb.grid(row=1, column=1, padx=8)
        theme_cb.bind("<<ComboboxSelected>>", self._on_style_changed)

        tk.Label(style_card, text="Card Shape:", bg="#1E1B2B", fg="#CBD5E1").grid(row=1, column=2, sticky="w", padx=(10, 0))
        self.shape_var = tk.StringVar(value=BASIC_WIDGET_SHAPES[self.basic_shape_idx]["name"])
        shape_cb = ttk.Combobox(style_card, textvariable=self.shape_var, values=[s["name"] for s in BASIC_WIDGET_SHAPES], state="readonly", width=24)
        shape_cb.grid(row=1, column=3, padx=8)
        shape_cb.bind("<<ComboboxSelected>>", self._on_style_changed)

        tk.Label(style_card, text="Gauge Design:", bg="#1E1B2B", fg="#CBD5E1").grid(row=1, column=4, sticky="w", padx=(10, 0))
        self.design_var = tk.StringVar(value=BASIC_WIDGET_DESIGNS[self.basic_design_idx]["name"])
        design_cb = ttk.Combobox(style_card, textvariable=self.design_var, values=[d["name"] for d in BASIC_WIDGET_DESIGNS], state="readonly", width=24)
        design_cb.grid(row=1, column=5, padx=8)
        design_cb.bind("<<ComboboxSelected>>", self._on_style_changed)

        # Quick Action Toolbar
        qbar = tk.Frame(outer, bg="#13111C")
        qbar.pack(fill="x", pady=6)
        tk.Button(qbar, text="Enable All 8 Core Widgets", bg="#7C3AED", fg="#FFFFFF", relief="flat", padx=12, pady=4, command=self._enable_all_basic).pack(side="left", padx=(0, 6))
        tk.Button(qbar, text="Enable Music + Visualizer", bg="#2563EB", fg="#FFFFFF", relief="flat", padx=12, pady=4, command=self._enable_music_vis).pack(side="left", padx=6)
        tk.Button(qbar, text="Disable All Basic Widgets", bg="#334155", fg="#FFFFFF", relief="flat", padx=12, pady=4, command=self._disable_all_basic).pack(side="left", padx=6)

        # Grid of Basic Widgets + Media + Visualizers
        grid_frame = tk.Frame(outer, bg="#13111C")
        grid_frame.pack(fill="both", expand=True, pady=6)

        basic_skins = [s for s in self.skins if s.get("is_basic")]
        for idx, s in enumerate(basic_skins):
            r, col = divmod(idx, 3)
            is_on = self.skin_state[s["key"]]["active"]
            wcard = tk.Frame(grid_frame, bg="#1E1B2B", padx=12, pady=10, highlightthickness=1, highlightbackground="#00C3FF" if is_on else "#2E2942")
            wcard.grid(row=r, column=col, sticky="nsew", padx=5, pady=5)
            grid_frame.grid_columnconfigure(col, weight=1)

            tk.Label(wcard, text=s["title"], bg="#1E1B2B", fg="#FFFFFF", font=("Segoe UI", 10, "bold")).pack(anchor="w")
            tk.Label(wcard, text=s["subtitle"], bg="#1E1B2B", fg="#94A3B8", font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 6))
            tk.Button(
                wcard,
                text="ON ✓" if is_on else "Turn ON",
                bg="#10B981" if is_on else "#312E43",
                fg="#FFFFFF",
                relief="flat",
                padx=10,
                command=lambda k=s["key"]: self._toggle_widget(k),
            ).pack(side="right")

    def _on_style_changed(self, _event=None):
        for i, t in enumerate(BASIC_WIDGET_THEMES):
            if t["name"] == self.theme_var.get():
                self.basic_theme_idx = i
        for i, s in enumerate(BASIC_WIDGET_SHAPES):
            if s["name"] == self.shape_var.get():
                self.basic_shape_idx = i
        for i, d in enumerate(BASIC_WIDGET_DESIGNS):
            if d["name"] == self.design_var.get():
                self.basic_design_idx = i
        write_basic_theme(
            BASIC_WIDGET_THEMES[self.basic_theme_idx],
            BASIC_WIDGET_SHAPES[self.basic_shape_idx],
            BASIC_WIDGET_DESIGNS[self.basic_design_idx],
        )
        self.relaunch_desktop_widgets()

    def _toggle_widget(self, key):
        self.skin_state[key]["active"] = not self.skin_state[key]["active"]
        save_global_config(self.skins, self.skin_state)
        self._build_basic_tab()
        self._build_suites_tab()
        self.relaunch_desktop_widgets()

    def _enable_all_basic(self):
        for s in self.skins:
            if s["is_suite"]:
                self.skin_state[s["key"]]["active"] = False
            elif s.get("is_basic") and s["title"].startswith("Basic"):
                self.skin_state[s["key"]]["active"] = True
        save_global_config(self.skins, self.skin_state)
        self._build_basic_tab()
        self._build_suites_tab()
        self.relaunch_desktop_widgets()

    def _enable_music_vis(self):
        for s in self.skins:
            if s["is_suite"]:
                self.skin_state[s["key"]]["active"] = False
            elif s["title"] in ("MusicBanner", "AudioVisualizer"):
                self.skin_state[s["key"]]["active"] = True
        save_global_config(self.skins, self.skin_state)
        self._build_basic_tab()
        self._build_suites_tab()
        self.relaunch_desktop_widgets()

    def _disable_all_basic(self):
        for s in self.skins:
            if s.get("is_basic"):
                self.skin_state[s["key"]]["active"] = False
        save_global_config(self.skins, self.skin_state)
        self._build_basic_tab()
        self.relaunch_desktop_widgets()

    # --- TAB 3: WIDGETS & POSITION CANVAS ---
    def _build_position_tab(self):
        for w in self.tab_position.winfo_children():
            w.destroy()

        pane = tk.Frame(self.tab_position, bg="#13111C", padx=16, pady=12)
        pane.pack(fill="both", expand=True)

        left = tk.Frame(pane, bg="#1E1B2B", width=300, padx=12, pady=12)
        left.pack(side="left", fill="y", padx=(0, 12))

        tk.Label(left, text="Select Widget to Position", bg="#1E1B2B", fg="#FFFFFF", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.pos_listbox = tk.Listbox(left, bg="#13111C", fg="#FFFFFF", selectbackground="#7C3AED", height=18, width=34, relief="flat")
        self.pos_listbox.pack(fill="both", expand=True, pady=8)
        self.pos_keys = []
        for s in self.skins:
            self.pos_keys.append(s["key"])
            mark = "● " if self.skin_state[s["key"]]["active"] else "○ "
            self.pos_listbox.insert("end", f"{mark}{s['title']}")
        self.pos_listbox.bind("<<ListboxSelect>>", self._on_pos_list_select)

        right = tk.Frame(pane, bg="#1E1B2B", padx=16, pady=12)
        right.pack(side="left", fill="both", expand=True)

        tk.Label(
            right,
            text="Interactive Monitor Positioner Canvas (Drag Selected Box Here — Widgets Stay Pinned on Desktop)",
            bg="#1E1B2B",
            fg="#FFFFFF",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")

        self.pos_canvas = tk.Canvas(right, bg="#0F172A", height=320, highlightthickness=2, highlightbackground="#334155")
        self.pos_canvas.pack(fill="x", pady=10)
        self.pos_canvas.bind("<ButtonPress-1>", self._on_canvas_drag_start)
        self.pos_canvas.bind("<B1-Motion>", self._on_canvas_drag_motion)
        self.pos_canvas.bind("<ButtonRelease-1>", self._on_canvas_drag_end)
        self.pos_canvas.bind("<Configure>", lambda _e: self._draw_position_canvas())

        # Quick 9-Anchor Preset Bar
        abar = tk.Frame(right, bg="#1E1B2B")
        abar.pack(fill="x", pady=6)
        for lbl, ax, ay in [
            ("↖ Top-Left", "left", "top"),
            ("↑ Top-Center", "center", "top"),
            ("↗ Top-Right", "right", "top"),
            ("• Center", "center", "center"),
            ("↙ Bottom-Left", "left", "bottom"),
            ("↓ Bottom-Center", "center", "bottom"),
            ("↘ Bottom-Right", "right", "bottom"),
        ]:
            tk.Button(
                abar,
                text=lbl,
                bg="#312E43",
                fg="#FFFFFF",
                relief="flat",
                padx=8,
                pady=3,
                command=lambda x=ax, y=ay: self._set_quick_anchor(x, y),
            ).pack(side="left", padx=3)

    def _on_pos_list_select(self, _event=None):
        sel = self.pos_listbox.curselection()
        if sel:
            self.selected_key = self.pos_keys[sel[0]]
            self._draw_position_canvas()

    def _set_quick_anchor(self, ax, ay):
        if not self.selected_key:
            return
        st = self.skin_state[self.selected_key]
        st["use_custom_pos"] = False
        st["anchor_x"] = ax
        st["anchor_y"] = ay
        save_global_config(self.skins, self.skin_state)
        self._draw_position_canvas()
        self.relaunch_desktop_widgets()

    def _draw_position_canvas(self):
        c = self.pos_canvas
        c.delete("all")
        cw = max(480, c.winfo_width())
        ch = max(260, c.winfo_height())
        sw = max(1366, self.root.winfo_screenwidth())
        sh = max(768, self.root.winfo_screenheight())
        scale = min((cw - 24) / sw, (ch - 24) / sh)
        ox = (cw - sw * scale) / 2
        oy = (ch - sh * scale) / 2

        c.create_rectangle(ox, oy, ox + sw * scale, oy + sh * scale, fill="#162038", outline="#38BDF8", width=2)

        for s in self.skins:
            key = s["key"]
            st = self.skin_state[key]
            if not st["active"] and key != self.selected_key:
                continue
            w, h = s["est_w"], s["est_h"]
            if st["use_custom_pos"]:
                x, y = st["x"], st["y"]
            else:
                x = (sw - w) // 2 if st["anchor_x"] == "center" else (sw - w - 24 if st["anchor_x"] == "right" else 24)
                y = (sh - h) // 2 if st["anchor_y"] == "center" else (sh - h - 48 if st["anchor_y"] == "bottom" else 36)
            rx1 = ox + x * scale
            ry1 = oy + y * scale
            rx2 = rx1 + max(48, w * scale)
            ry2 = ry1 + max(26, h * scale)
            is_sel = key == self.selected_key
            c.create_rectangle(
                rx1,
                ry1,
                rx2,
                ry2,
                fill="#0284C7" if is_sel else "#4C1D95",
                outline="#38BDF8" if is_sel else "#A78BFA",
                width=2,
            )
            c.create_text((rx1 + rx2) / 2, (ry1 + ry2) / 2, text=s["title"][:14], fill="#FFFFFF", font=("Segoe UI", 8, "bold"))

    def _on_canvas_drag_start(self, event):
        self._drag_origin = (event.x, event.y)

    def _on_canvas_drag_motion(self, event):
        if not self.selected_key:
            return
        cw = max(480, self.pos_canvas.winfo_width())
        ch = max(260, self.pos_canvas.winfo_height())
        sw = max(1366, self.root.winfo_screenwidth())
        sh = max(768, self.root.winfo_screenheight())
        scale = min((cw - 24) / sw, (ch - 24) / sh)
        ox = (cw - sw * scale) / 2
        oy = (ch - sh * scale) / 2
        new_x = int(max(0, min(sw - 120, (event.x - ox) / max(0.05, scale) - 60)))
        new_y = int(max(0, min(sh - 60, (event.y - oy) / max(0.05, scale) - 30)))
        st = self.skin_state[self.selected_key]
        st["use_custom_pos"] = True
        st["x"] = new_x
        st["y"] = new_y
        self._draw_position_canvas()

    def _on_canvas_drag_end(self, _event):
        save_global_config(self.skins, self.skin_state)
        self.relaunch_desktop_widgets()

    # --- DESKTOP WIDGET ENGINE LIFECYCLE ---
    def relaunch_desktop_widgets(self):
        for w in self.active_desktop_windows:
            w.destroy()
        self.active_desktop_windows = []
        if not self.engine_running:
            return
        for s in self.skins:
            st = self.skin_state.get(s["key"])
            if st and st.get("active"):
                win = DesktopWidgetWindow(self.root, s, st, self.telemetry, self.open_weather_popup)
                self.active_desktop_windows.append(win)

    def _on_toggle_power(self):
        self.engine_running = not self.engine_running
        if self.engine_running:
            self.power_btn.configure(text="Turn OFF Widgets", bg="#DC2626")
            self.status_lbl.configure(text="● Desktop Widgets Active (Pinned)", fg="#34D399")
        else:
            self.power_btn.configure(text="Turn ON Widgets", bg="#10B981")
            self.status_lbl.configure(text="○ Desktop Widgets Stopped", fg="#94A3B8")
        self.relaunch_desktop_widgets()

    def open_weather_popup(self):
        WeatherForecastPopupWindow(self.root, on_location_changed=self._on_weather_updated)

    def _on_weather_updated(self):
        self.telemetry.refresh_weather_async(force=True)
        for w in self.active_desktop_windows:
            w.redraw()

    def _on_install_skin(self):
        path = filedialog.askopenfilename(
            title="Install Rainmeter Skin (.rmskin, .ini, or .zip)",
            filetypes=[("Rainmeter Skins", "*.rmskin *.ini *.zip")],
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
            self._build_position_tab()
            messagebox.showinfo("Trad Rainmeter", f"Installed skin package: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Install Failed", str(e))

    def _on_export_rmskin(self):
        if build_rmskin_package is None:
            messagebox.showerror("Export .rmskin", "build_rmskin module not found.")
            return
        save_to = filedialog.asksaveasfilename(
            title="Export Windows Rainmeter .rmskin Package",
            defaultextension=".rmskin",
            initialfile="TradRainmeter_1.1.0.rmskin",
            filetypes=[("Rainmeter Skin Package", "*.rmskin")],
        )
        if not save_to:
            return
        try:
            out = build_rmskin_package(output_path=save_to, version="1.1.0", config_dir=CONFIG_DIR)
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
    TradRainmeterWindowsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

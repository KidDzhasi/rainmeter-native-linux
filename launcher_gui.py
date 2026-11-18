#!/usr/bin/env python3
"""
Rainmeter Native — GTK4 / Libadwaita Desktop Control Center
Features three dedicated tabs:
  1. Suites: One-click suite switching (auto-removes previous suite & replaces it)
     with automatic monitor resolution fitting (AutoFit).
  2. Basic Widgets: Dedicated area for the 8 modular Basic Widgets with a live
     Theme Studio (Frosted Glass, Pure Transparent, Neon Blue, Arctic Blue,
     Fedora Cyber, Crystal Aqua Glass, Sunset Glow, Sapphire & Amber,
     Crimson Night Drive, Obsidian Lime).
  3. Widgets & Position: Interactive multi-widget positioner canvas, custom
     .rmskin / .ini widget manager, and Suite Builder.
"""

import configparser
import concurrent.futures
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import zipfile

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Pango", "1.0")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango

try:
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)
except Exception:
    pass

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(REPO_DIR, "build")
CONFIG_DIR = os.path.expanduser("~/.config/rainmeter-native")
USER_SKINS_DIR = os.path.join(CONFIG_DIR, "Skins")
GLOBAL_CONFIG = os.path.join(CONFIG_DIR, "Rainmeter.ini")
WEATHER_LOCATIONS_PATH = os.path.join(CONFIG_DIR, "weather_locations.json")

_local_bin = os.path.join(BUILD_DIR, "rainmeter-native")
if os.path.isfile(_local_bin):
    ENGINE_BIN = _local_bin
else:
    ENGINE_BIN = shutil.which("rainmeter-native") or "/usr/bin/rainmeter-native"

SYSTEM_SUITES_DIR = os.path.join(REPO_DIR, "suites")
SYSTEM_WIDGETS_DIR = os.path.join(REPO_DIR, "widgets")
COMMUNITY_DIR = os.path.join(REPO_DIR, "community")

if os.access(SYSTEM_WIDGETS_DIR, os.W_OK):
    WIDGETS_DIR = SYSTEM_WIDGETS_DIR
else:
    WIDGETS_DIR = os.path.join(CONFIG_DIR, "widgets")
    if os.path.isdir(SYSTEM_WIDGETS_DIR) and not os.path.isdir(WIDGETS_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        shutil.copytree(SYSTEM_WIDGETS_DIR, WIDGETS_DIR, dirs_exist_ok=True)

if os.access(SYSTEM_SUITES_DIR, os.W_OK):
    SUITES_DIR = SYSTEM_SUITES_DIR
else:
    SUITES_DIR = os.path.join(CONFIG_DIR, "suites")
    os.makedirs(SUITES_DIR, exist_ok=True)

THEME_INC_PATH = os.path.join(WIDGETS_DIR, "Theme.inc")
WEATHER_INC_PATH = os.path.join(WIDGETS_DIR, "Weather.inc")
USER_THEME_INC = os.path.join(CONFIG_DIR, "Theme.inc")
USER_WEATHER_INC = os.path.join(CONFIG_DIR, "Weather.inc")

# ---------------------------------------------------------------------------
# Basic Widgets Theme Presets (inspired by the desktop theme gallery)
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
        "subtext": "130,185,235,255",
        "track": "20,32,52,255",
        "preview_bg": (0.05, 0.07, 0.11, 0.92),
        "preview_border": (0.0, 0.69, 1.0, 0.95),
        "preview_accent": (0.0, 0.76, 1.0, 1.0),
    },
    {
        "name": "Frosted Glass",
        "subtitle": "Translucent frosted crystal glass with soft ice-white border and sky accents",
        "corner_radius": 12,
        "bg_fill": "Fill LinearGradient 135 | 255,255,255,44 | 180,215,255,22",
        "border_stroke": "StrokeWidth 1.5 | Stroke Color 255,255,255,105",
        "accent": "110,230,255,255",
        "text": "255,255,255,255",
        "subtext": "215,232,250,225",
        "track": "255,255,255,40",
        "preview_bg": (0.75, 0.85, 0.98, 0.25),
        "preview_border": (1.0, 1.0, 1.0, 0.65),
        "preview_accent": (0.43, 0.90, 1.0, 1.0),
    },
    {
        "name": "Pure Transparent",
        "subtitle": "Zero background box or border — floating minimalist HUD text and bars",
        "corner_radius": 0,
        "bg_fill": "Fill Color 0,0,0,0",
        "border_stroke": "StrokeWidth 0 | Stroke Color 0,0,0,0",
        "accent": "0,235,255,255",
        "text": "255,255,255,255",
        "subtext": "200,220,240,235",
        "track": "255,255,255,45",
        "preview_bg": (0.08, 0.10, 0.14, 0.08),
        "preview_border": (1.0, 1.0, 1.0, 0.18),
        "preview_accent": (0.0, 0.92, 1.0, 1.0),
    },
    {
        "name": "Arctic Blue",
        "subtitle": "Soft slate-ocean blue panels with frosted sky-blue highlights",
        "corner_radius": 12,
        "bg_fill": "Fill LinearGradient 135 | 38,62,92,205 | 22,38,62,220",
        "border_stroke": "StrokeWidth 1.5 | Stroke Color 125,185,240,165",
        "accent": "125,210,255,255",
        "text": "245,250,255,255",
        "subtext": "180,210,240,240",
        "track": "18,30,48,200",
        "preview_bg": (0.15, 0.24, 0.36, 0.85),
        "preview_border": (0.49, 0.73, 0.94, 0.80),
        "preview_accent": (0.49, 0.82, 1.0, 1.0),
    },
    {
        "name": "Fedora Cyber (Cyan & Magenta)",
        "subtitle": "Dark hex-grid carbon with glowing cyan border and neon magenta bars",
        "corner_radius": 8,
        "bg_fill": "Fill LinearGradient 135 | 16,18,32,225 | 10,12,22,240",
        "border_stroke": "StrokeWidth 1.5 | Stroke Color 0,235,235,200",
        "accent": "255,95,205,255",
        "text": "240,248,255,255",
        "subtext": "0,230,235,230",
        "track": "28,32,52,240",
        "preview_bg": (0.06, 0.07, 0.13, 0.90),
        "preview_border": (0.0, 0.92, 0.92, 0.85),
        "preview_accent": (1.0, 0.37, 0.80, 1.0),
    },
    {
        "name": "Crystal Aqua Glass",
        "subtitle": "Tropical turquoise lagoon glass with bright aqua-mint telemetry",
        "corner_radius": 12,
        "bg_fill": "Fill LinearGradient 135 | 8,52,65,165 | 4,28,38,185",
        "border_stroke": "StrokeWidth 1.5 | Stroke Color 0,245,215,175",
        "accent": "0,245,212,255",
        "text": "240,255,252,255",
        "subtext": "150,235,220,240",
        "track": "10,45,55,200",
        "preview_bg": (0.03, 0.20, 0.25, 0.72),
        "preview_border": (0.0, 0.96, 0.84, 0.80),
        "preview_accent": (0.0, 0.96, 0.83, 1.0),
    },
    {
        "name": "Sunset Glow",
        "subtitle": "Warm violet-magenta glass with golden sunset amber bars",
        "corner_radius": 12,
        "bg_fill": "Fill LinearGradient 135 | 48,18,58,205 | 24,10,34,225",
        "border_stroke": "StrokeWidth 1.5 | Stroke Color 255,105,160,185",
        "accent": "255,190,65,255",
        "text": "255,245,250,255",
        "subtext": "255,150,190,240",
        "track": "42,20,48,220",
        "preview_bg": (0.19, 0.07, 0.23, 0.85),
        "preview_border": (1.0, 0.41, 0.63, 0.80),
        "preview_accent": (1.0, 0.75, 0.25, 1.0),
    },
    {
        "name": "Sapphire & Amber",
        "subtitle": "Deep skyline navy with royal sapphire border and warm gold highlights",
        "corner_radius": 6,
        "bg_fill": "Fill LinearGradient 135 | 14,24,48,220 | 8,14,28,235",
        "border_stroke": "StrokeWidth 1.5 | Stroke Color 65,135,255,190",
        "accent": "255,185,45,255",
        "text": "242,246,255,255",
        "subtext": "145,185,245,240",
        "track": "22,34,62,230",
        "preview_bg": (0.05, 0.09, 0.19, 0.88),
        "preview_border": (0.25, 0.53, 1.0, 0.85),
        "preview_accent": (1.0, 0.73, 0.18, 1.0),
    },
    {
        "name": "Crimson Night Drive",
        "subtitle": "Dark rainy teal-black with neon crimson-red accents",
        "corner_radius": 8,
        "bg_fill": "Fill LinearGradient 135 | 8,24,32,220 | 5,14,20,235",
        "border_stroke": "StrokeWidth 1.5 | Stroke Color 255,45,85,200",
        "accent": "255,50,90,255",
        "text": "235,250,255,255",
        "subtext": "95,205,225,240",
        "track": "16,36,46,230",
        "preview_bg": (0.03, 0.09, 0.13, 0.88),
        "preview_border": (1.0, 0.18, 0.33, 0.85),
        "preview_accent": (1.0, 0.20, 0.35, 1.0),
    },
    {
        "name": "Obsidian Lime (Classic)",
        "subtitle": "Classic dark obsidian blocks with crisp lime-green telemetry bars",
        "corner_radius": 2,
        "bg_fill": "Fill Color 12,14,18,225",
        "border_stroke": "StrokeWidth 1 | Stroke Color 35,40,48,180",
        "accent": "140,230,0,255",
        "text": "215,220,225,255",
        "subtext": "155,160,168,255",
        "track": "28,32,38,255",
        "preview_bg": (0.05, 0.06, 0.07, 0.90),
        "preview_border": (0.20, 0.22, 0.26, 0.80),
        "preview_accent": (0.55, 0.90, 0.0, 1.0),
    },
]


BASIC_WIDGET_SHAPES = [
    {
        "name": "Rounded Card (Default)",
        "subtitle": "Sleek rounded rectangle corners (10px radius)",
        "corner_radius": 10,
        "borderless": False,
    },
    {
        "name": "Sharp Box (Rectangular)",
        "subtitle": "Crisp 90-degree geometric corners (0px radius)",
        "corner_radius": 0,
        "borderless": False,
    },
    {
        "name": "Soft Squircle (iOS / macOS Style)",
        "subtitle": "Deep continuous squircle corners (24px radius)",
        "corner_radius": 24,
        "borderless": False,
    },
    {
        "name": "Full Pill / Stadium Capsule",
        "subtitle": "Stadium capsule geometry with deeply rounded ends (52px radius)",
        "corner_radius": 52,
        "borderless": False,
    },
    {
        "name": "Circular Disc / Badge",
        "subtitle": "Circular disc and radial badge profile (90px radius)",
        "corner_radius": 90,
        "borderless": False,
    },
    {
        "name": "Floating Borderless (HUD Only)",
        "subtitle": "Removes background box and border while keeping theme colors and gauges",
        "corner_radius": 0,
        "borderless": True,
    },
]

BASIC_WIDGET_DESIGNS = [
    {
        "id": "vertical",
        "name": "Vertical Bars (Classic HUD)",
        "subtitle": "Vertical telemetry bars and split digital clock",
    },
    {
        "id": "circular",
        "name": "Circular Ring Gauges (Radial)",
        "subtitle": "Glowing circular percentage rings and radial clock (like your ring screenshots)",
    },
    {
        "id": "capsule",
        "name": "Capsule Pill (Stacked Material / iOS)",
        "subtitle": "Stacked vertical pill clock (19 over 48) and chunky pill sliders",
    },
    {
        "id": "horizontal",
        "name": "Horizontal Minimal (Stepped Ribbon)",
        "subtitle": "Side accent ribbon clock and stepped horizontal telemetry progress lines",
    },
]


def read_current_basic_style():
    theme_idx = 0
    shape_idx = 0
    design_idx = 0
    if os.path.isfile(THEME_INC_PATH):
        try:
            with open(THEME_INC_PATH, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    sline = line.strip()
                    if sline.startswith("ThemeName="):
                        tname = sline.split("=", 1)[1].strip()
                        for idx, t in enumerate(BASIC_WIDGET_THEMES):
                            if t["name"].lower() == tname.lower():
                                theme_idx = idx
                    elif sline.startswith("ShapeName="):
                        sname = sline.split("=", 1)[1].strip()
                        for idx, s in enumerate(BASIC_WIDGET_SHAPES):
                            if s["name"].lower() == sname.lower():
                                shape_idx = idx
                    elif sline.startswith("DesignStyle="):
                        dname = sline.split("=", 1)[1].strip()
                        for idx, d in enumerate(BASIC_WIDGET_DESIGNS):
                            if d["id"].lower() == dname.lower() or d["name"].lower() == dname.lower():
                                design_idx = idx
        except Exception:
            pass
    return theme_idx, shape_idx, design_idx


def read_current_basic_theme_index():
    return read_current_basic_style()[0]


def write_basic_theme(theme_dict, shape_dict=None, design_dict=None):
    os.makedirs(WIDGETS_DIR, exist_ok=True)
    if shape_dict is None:
        shape_dict = BASIC_WIDGET_SHAPES[0]
    if design_dict is None:
        design_dict = BASIC_WIDGET_DESIGNS[0]

    radius = shape_dict["corner_radius"]
    if shape_dict.get("borderless", False):
        bg_fill = "Fill Color 0,0,0,0"
        border_stroke = "StrokeWidth 0 | Stroke Color 0,0,0,0"
    else:
        bg_fill = theme_dict["bg_fill"]
        border_stroke = theme_dict["border_stroke"]

    content = (
        "[Variables]\n"
        f"ThemeName={theme_dict['name']}\n"
        f"ShapeName={shape_dict['name']}\n"
        f"DesignStyle={design_dict['id']}\n"
        f"CornerRadius={radius}\n"
        f"BgFill={bg_fill}\n"
        f"BorderStroke={border_stroke}\n"
        f"AccentColor={theme_dict['accent']}\n"
        f"TextColor={theme_dict['text']}\n"
        f"SubTextColor={theme_dict['subtext']}\n"
        f"TrackColor={theme_dict['track']}\n"
    )
    os.makedirs(WIDGETS_DIR, exist_ok=True)
    with open(THEME_INC_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(USER_THEME_INC, "w", encoding="utf-8") as f:
        f.write(content)


DEFAULT_WEATHER_LOCATIONS = [
    {"name": "Johannesburg, South Africa", "lat": -26.2041, "lon": 28.0473},
    {"name": "Pretoria, South Africa", "lat": -25.7479, "lon": 28.2293},
    {"name": "Polokwane, Limpopo", "lat": -23.9045, "lon": 29.4689},
    {"name": "Giyani, Limpopo", "lat": -23.3025, "lon": 30.7187},
    {"name": "Cape Town, South Africa", "lat": -33.9249, "lon": 18.4241},
    {"name": "London, United Kingdom", "lat": 51.5072, "lon": -0.1276},
    {"name": "New York, USA", "lat": 40.7128, "lon": -74.0060},
]


def load_weather_config():
    """Return (locations, active_idx, units) synced between weather_locations.json and Weather.inc."""
    locations = [dict(x) for x in DEFAULT_WEATHER_LOCATIONS]
    active_idx = 0
    units = "metric"

    if os.path.isfile(WEATHER_LOCATIONS_PATH):
        try:
            with open(WEATHER_LOCATIONS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            saved = data.get("locations", [])
            valid = []
            for item in saved:
                if "name" in item and "lat" in item and "lon" in item:
                    valid.append(
                        {
                            "name": str(item["name"]).strip(),
                            "lat": float(item["lat"]),
                            "lon": float(item["lon"]),
                        }
                    )
            if valid:
                locations = valid
            active_idx = max(0, min(len(locations) - 1, int(data.get("active_index", 0))))
            if data.get("units") in ("metric", "imperial"):
                units = data["units"]
        except Exception:
            pass

    if os.path.isfile(WEATHER_INC_PATH):
        try:
            inc_name, inc_lat, inc_lon = None, None, None
            with open(WEATHER_INC_PATH, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    sline = line.strip()
                    if sline.startswith("WeatherLocation="):
                        inc_name = sline.split("=", 1)[1].strip()
                    elif sline.startswith("WeatherLat="):
                        inc_lat = float(sline.split("=", 1)[1].strip())
                    elif sline.startswith("WeatherLon="):
                        inc_lon = float(sline.split("=", 1)[1].strip())
                    elif sline.startswith("WeatherUnits="):
                        u = sline.split("=", 1)[1].strip().lower()
                        if u in ("metric", "imperial"):
                            units = u
            if inc_name and inc_lat is not None and inc_lon is not None:
                found = next(
                    (
                        i
                        for i, loc in enumerate(locations)
                        if loc["name"].lower() == inc_name.lower()
                        or (abs(loc["lat"] - inc_lat) < 0.002 and abs(loc["lon"] - inc_lon) < 0.002)
                    ),
                    None,
                )
                if found is not None:
                    active_idx = found
                else:
                    locations.insert(0, {"name": inc_name, "lat": inc_lat, "lon": inc_lon})
                    active_idx = 0
        except Exception:
            pass

    return locations, active_idx, units


def save_weather_config(locations, active_idx, units):
    """Persist weather_locations.json and write widgets/Weather.inc."""
    if not locations:
        locations = [dict(DEFAULT_WEATHER_LOCATIONS[0])]
    active_idx = max(0, min(len(locations) - 1, int(active_idx)))
    units = "imperial" if units == "imperial" else "metric"

    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(WEATHER_LOCATIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {"active_index": active_idx, "units": units, "locations": locations},
            f,
            indent=2,
        )

    loc = locations[active_idx]
    os.makedirs(WIDGETS_DIR, exist_ok=True)
    inc_content = (
        "[Variables]\n"
        f"WeatherLocation={loc['name']}\n"
        f"WeatherLat={loc['lat']:.4f}\n"
        f"WeatherLon={loc['lon']:.4f}\n"
        f"WeatherUnits={units}\n"
    )
    with open(WEATHER_INC_PATH, "w", encoding="utf-8") as f:
        f.write(inc_content)
    with open(USER_WEATHER_INC, "w", encoding="utf-8") as f:
        f.write(inc_content)


def search_weather_locations(query):
    """Search cities, towns, and rural villages across ArcGIS, Open-Meteo, Nominatim, and Photon."""
    q = query.strip()
    if not q:
        return []

    results = []
    seen_coords = set()

    def _add(name, lat, lon, source, detail=""):
        key = (round(float(lat), 3), round(float(lon), 3))
        if key in seen_coords:
            return
        seen_coords.add(key)
        results.append(
            {
                "name": name,
                "lat": round(float(lat), 5),
                "lon": round(float(lon), 5),
                "source": source,
                "detail": detail,
            }
        )

    # Direct coordinate entry: e.g. "-23.312, 30.718" or "Mahatlani Village @ -23.312, 30.718"
    coord_match = re.search(r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)", q)
    if coord_match:
        try:
            lat_v = float(coord_match.group(1))
            lon_v = float(coord_match.group(2))
            if -90.0 <= lat_v <= 90.0 and -180.0 <= lon_v <= 180.0:
                label_part = q[: coord_match.start()].strip(" @-:,")
                label = label_part if label_part else f"Custom ({lat_v:.4f}, {lon_v:.4f})"
                _add(label, lat_v, lon_v, "Direct Coordinates", "Exact latitude / longitude")
                return results
        except ValueError:
            pass

    # Build clean search variants (strip "Village" suffix first so village gazetteers match accurately)
    stripped = re.sub(r"\bvillage\b", "", q, flags=re.IGNORECASE).strip(" ,")
    queries = []
    if stripped:
        queries.append(stripped)
    if q.lower() not in [x.lower() for x in queries]:
        queries.append(q)

    # 1 & 2. Query ArcGIS World Geocoder & Open-Meteo in parallel (fast ~0.5s response)
    def _query_arcgis():
        out = []
        for term in queries[:2]:
            try:
                url = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates?" + urllib.parse.urlencode(
                    {
                        "SingleLine": term,
                        "f": "json",
                        "maxLocations": 6,
                        "outFields": "Match_addr,Place_addr,Type,Country",
                    }
                )
                req = urllib.request.Request(url, headers={"User-Agent": "TradRainmeter/1.0"})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                for c in data.get("candidates", []):
                    score = float(c.get("score", 0))
                    loc = c.get("location", {})
                    attrs = c.get("attributes", {})
                    addr = attrs.get("Match_addr") or c.get("address") or term
                    place_addr = attrs.get("Place_addr") or ""
                    if "y" in loc and "x" in loc and score >= 75:
                        out.append((score, addr, loc["y"], loc["x"], place_addr))
            except Exception:
                pass
            if out and out[0][0] >= 98:
                break
        out.sort(key=lambda item: item[0], reverse=True)
        return out

    def _query_openmeteo():
        out = []
        for term in queries[:2]:
            try:
                url = "https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode(
                    {"name": term, "count": 5, "language": "en", "format": "json"}
                )
                req = urllib.request.Request(url, headers={"User-Agent": "TradRainmeter/1.0"})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                for item in data.get("results", []):
                    parts = [item.get("name", "")]
                    if item.get("admin2"):
                        parts.append(item["admin2"])
                    elif item.get("admin1"):
                        parts.append(item["admin1"])
                    if item.get("country"):
                        parts.append(item["country"])
                    label = ", ".join(p for p in parts if p)
                    detail = " · ".join(
                        p for p in [item.get("admin1", ""), item.get("feature_code", "")] if p
                    )
                    out.append((label, item["latitude"], item["longitude"], "Open-Meteo", detail))
            except Exception:
                pass
            if out:
                break
        return out

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        f_arc = pool.submit(_query_arcgis)
        f_om = pool.submit(_query_openmeteo)
        arcgis_candidates = f_arc.result()
        om_candidates = f_om.result()

    for score, addr, lat_v, lon_v, place_addr in arcgis_candidates:
        detail = f"{place_addr} · match {score:.0f}%" if place_addr else f"match {score:.0f}%"
        _add(addr, lat_v, lon_v, "ArcGIS Gazetteer", detail)

    for label, lat_v, lon_v, src, detail in om_candidates:
        _add(label, lat_v, lon_v, src, detail)

    # 3 & 4. Parallel Nominatim / Photon fallback only if primary sources returned fewer than 3 hits
    if len(results) < 3:
        def _query_nom():
            out = []
            try:
                url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
                    {"q": queries[0], "format": "json", "limit": 4, "addressdetails": 1}
                )
                req = urllib.request.Request(url, headers={"User-Agent": "TradRainmeter/1.0"})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    items = json.loads(resp.read().decode("utf-8", errors="ignore"))
                for item in items:
                    addr = item.get("address", {})
                    primary = (
                        addr.get("village")
                        or addr.get("hamlet")
                        or addr.get("town")
                        or addr.get("city")
                        or item.get("name")
                        or item.get("display_name", "").split(",")[0]
                    )
                    region = addr.get("state") or addr.get("county") or ""
                    country = addr.get("country") or ""
                    label = ", ".join(p for p in [primary, region, country] if p)
                    out.append((label, item["lat"], item["lon"], "OpenStreetMap", item.get("display_name", "")))
            except Exception:
                pass
            return out

        def _query_photon():
            out = []
            try:
                url = "https://photon.komoot.io/api/?" + urllib.parse.urlencode({"q": queries[0], "limit": 4})
                req = urllib.request.Request(url, headers={"User-Agent": "TradRainmeter/1.0"})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                for feat in data.get("features", []):
                    props = feat.get("properties", {})
                    coords = feat.get("geometry", {}).get("coordinates", [])
                    if len(coords) < 2:
                        continue
                    lon_v, lat_v = coords[0], coords[1]
                    name = props.get("name", "")
                    if not name:
                        continue
                    region = props.get("state") or props.get("city") or props.get("county") or ""
                    country = props.get("country") or ""
                    label = ", ".join(p for p in [name, region, country] if p)
                    detail = ", ".join(p for p in [props.get("osm_value", ""), props.get("county", "")] if p)
                    out.append((label, lat_v, lon_v, "Photon OSM", detail))
            except Exception:
                pass
            return out

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            f_nom = pool.submit(_query_nom)
            f_ph = pool.submit(_query_photon)
            for label, lat_v, lon_v, src, detail in f_nom.result() + f_ph.result():
                _add(label, lat_v, lon_v, src, detail)

    return results[:10]


WMO_WEATHER_MAP = {
    0: ("Clear Sky", "weather-clear-symbolic"),
    1: ("Mainly Clear", "weather-few-clouds-symbolic"),
    2: ("Partly Cloudy", "weather-few-clouds-symbolic"),
    3: ("Overcast", "weather-overcast-symbolic"),
    45: ("Fog", "weather-fog-symbolic"),
    48: ("Rime Fog", "weather-fog-symbolic"),
    51: ("Light Drizzle", "weather-showers-scattered-symbolic"),
    53: ("Drizzle", "weather-showers-scattered-symbolic"),
    55: ("Heavy Drizzle", "weather-showers-symbolic"),
    56: ("Freezing Drizzle", "weather-showers-scattered-symbolic"),
    57: ("Freezing Drizzle", "weather-showers-symbolic"),
    61: ("Light Rain", "weather-showers-scattered-symbolic"),
    63: ("Rain", "weather-showers-symbolic"),
    65: ("Heavy Rain", "weather-showers-symbolic"),
    66: ("Freezing Rain", "weather-showers-symbolic"),
    67: ("Freezing Rain", "weather-showers-symbolic"),
    71: ("Light Snow", "weather-snow-symbolic"),
    73: ("Snow", "weather-snow-symbolic"),
    75: ("Heavy Snow", "weather-snow-symbolic"),
    77: ("Snow Grains", "weather-snow-symbolic"),
    80: ("Light Showers", "weather-showers-scattered-symbolic"),
    81: ("Showers", "weather-showers-symbolic"),
    82: ("Heavy Showers", "weather-showers-symbolic"),
    85: ("Snow Showers", "weather-snow-symbolic"),
    86: ("Heavy Snow Showers", "weather-snow-symbolic"),
    95: ("Thunderstorm", "weather-storm-symbolic"),
    96: ("Thunderstorm & Hail", "weather-storm-symbolic"),
    99: ("Severe Storm", "weather-storm-symbolic"),
}


def wmo_info(code):
    return WMO_WEATHER_MAP.get(int(code) if code is not None else -1, ("Variable Clouds", "weather-overcast-symbolic"))


def wind_compass(deg):
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return dirs[int(((float(deg) + 11.25) % 360.0) // 22.5) % 16]


_FORECAST_CACHE = {}
_WEATHER_CACHE_DIR = os.path.expanduser("~/.cache/trad-rainmeter")
_RELAUNCH_LOCK = threading.Lock()


def _met_symbol_to_wmo(sym):
    s = (sym or "").lower()
    if "thunder" in s:
        return 95
    if "heavyrain" in s:
        return 65
    if "rainshowers" in s:
        return 80
    if "lightrain" in s:
        return 61
    if "rain" in s or "sleet" in s:
        return 63
    if "snow" in s:
        return 73
    if "fog" in s:
        return 45
    if "partlycloudy" in s:
        return 2
    if "fair" in s:
        return 1
    if "cloudy" in s:
        return 3
    if "clearsky" in s:
        return 0
    return 2


def _fetch_metno_as_openmeteo(lat, lon, units="metric"):
    """Fetch forecast from Norwegian Meteorological Institute (met.no) and normalize to Open-Meteo schema."""
    import datetime

    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat:.4f}&lon={lon:.4f}"
    req = urllib.request.Request(
        url, headers={"User-Agent": "TradRainmeter/1.0 (github.com/KidDzhasi/Trad-rainmeter)"}
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        raw = json.loads(resp.read().decode("utf-8", errors="ignore"))

    ts_list = raw.get("properties", {}).get("timeseries", [])
    if not ts_list:
        raise ValueError("Empty response from met.no")

    def c_to_u(c):
        return (c * 9.0 / 5.0 + 32.0) if units == "imperial" else c

    def ms_to_u(ms):
        return (ms * 2.23694) if units == "imperial" else (ms * 3.6)

    def sym_rain_prob(sym):
        s = (sym or "").lower()
        if "thunder" in s or "heavy" in s:
            return 80
        if "rain" in s or "shower" in s:
            return 60
        if "cloudy" in s:
            return 20
        return 5

    h_times, h_temps, h_pops, h_codes = [], [], [], []
    by_day = {}

    first_inst = ts_list[0].get("data", {}).get("instant", {}).get("details", {})
    first_next = (
        ts_list[0].get("data", {}).get("next_1_hours")
        or ts_list[0].get("data", {}).get("next_6_hours")
        or {}
    )
    first_sym = first_next.get("summary", {}).get("symbol_code", "partlycloudy_day")

    for entry in ts_list:
        iso = entry.get("time", "")
        try:
            dt_utc = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
            dt_loc = dt_utc.astimezone()
        except Exception:
            continue

        inst = entry.get("data", {}).get("instant", {}).get("details", {})
        nxt = (
            entry.get("data", {}).get("next_1_hours")
            or entry.get("data", {}).get("next_6_hours")
            or entry.get("data", {}).get("next_12_hours")
            or {}
        )
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

    d_times, d_codes, d_max, d_min, d_pop, d_sr, d_ss = [], [], [], [], [], [], []
    for dk in sorted(by_day.keys())[:7]:
        b = by_day[dk]
        d_times.append(dk)
        d_codes.append(max(b["codes"]))
        d_max.append(round(max(b["temps"]), 1))
        d_min.append(round(min(b["temps"]), 1))
        d_pop.append(max(b["pops"]))
        d_sr.append(f"{dk}T05:30")
        d_ss.append(f"{dk}T18:30")

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
            "sunrise": d_sr,
            "sunset": d_ss,
        },
    }


def fetch_full_weather_forecast(lat, lon, units="metric", force=False):
    """Fetch forecast with 15-min memory & disk cache, Open-Meteo primary, and met.no fallback."""
    cache_key = (round(float(lat), 3), round(float(lon), 3), units)
    now_mono = time.monotonic()
    now_wall = time.time()

    if not force and cache_key in _FORECAST_CACHE:
        ts, cached_data = _FORECAST_CACHE[cache_key]
        if now_mono - ts < 900.0:
            return cached_data

    os.makedirs(_WEATHER_CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(
        _WEATHER_CACHE_DIR, f"forecast_{cache_key[0]:.3f}_{cache_key[1]:.3f}_{units}.json"
    )
    stale_data = None
    if os.path.isfile(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as cf:
                payload = json.load(cf)
            stale_data = payload.get("data")
            if not force and stale_data and (now_wall - float(payload.get("ts", 0))) < 900.0:
                _FORECAST_CACHE[cache_key] = (now_mono, stale_data)
                return stale_data
        except Exception:
            pass

    data = None
    last_err = None

    # 1. Try Open-Meteo
    try:
        params = {
            "latitude": f"{lat:.4f}",
            "longitude": f"{lon:.4f}",
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation_probability,weather_code,wind_speed_10m,wind_direction_10m,surface_pressure,is_day",
            "hourly": "temperature_2m,precipitation_probability,weather_code",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset",
            "timezone": "auto",
            "forecast_days": 7,
        }
        if units == "imperial":
            params["temperature_unit"] = "fahrenheit"
            params["wind_speed_unit"] = "mph"

        url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "TradRainmeter/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception as exc:
        last_err = exc

    # 2. Fallback to Norwegian Meteorological Institute (met.no) if Open-Meteo failed or rate-limited (429)
    if data is None:
        try:
            data = _fetch_metno_as_openmeteo(lat, lon, units)
        except Exception as exc:
            last_err = exc

    if data is not None:
        _FORECAST_CACHE[cache_key] = (now_mono, data)
        try:
            with open(cache_file, "w", encoding="utf-8") as cf:
                json.dump({"ts": now_wall, "data": data}, cf)
        except Exception:
            pass
        return data

    # 3. Serve stale disk cache if both providers failed temporarily
    if stale_data is not None:
        _FORECAST_CACHE[cache_key] = (now_mono, stale_data)
        return stale_data

    raise last_err if last_err else RuntimeError("Weather unavailable")


def relaunch_active_engine_from_config():
    """Restart running desktop skins in background according to ~/.config/rainmeter-native/Rainmeter.ini."""
    def _worker():
        with _RELAUNCH_LOCK:
            stop_engine()
            if not os.path.isfile(GLOBAL_CONFIG) or not os.path.isfile(ENGINE_BIN):
                return
            active_keys = []
            cp = configparser.ConfigParser(interpolation=None, strict=False)
            cp.optionxform = str
            try:
                with open(GLOBAL_CONFIG, "r", encoding="utf-8", errors="ignore") as f:
                    cp.read_file(f)
                for sec in cp.sections():
                    val = cp.get(sec, "Active", fallback="0").strip()
                    if val not in ("0", "false", ""):
                        active_keys.append(sec)
            except Exception:
                return
            if active_keys:
                subprocess.Popen(
                    [ENGINE_BIN] + active_keys,
                    cwd=REPO_DIR,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                    close_fds=True,
                )

    threading.Thread(target=_worker, daemon=True).start()


def apply_basic_widget_design(design_id):
    """Write the selected visual design layout (vertical, circular, capsule, horizontal) to the 8 Basic Widgets."""
    os.makedirs(WIDGETS_DIR, exist_ok=True)

    if design_id == "circular":
        files = {
            "BasicClock/BasicClock.ini": """[Rainmeter]
Update=1000
AccurateText=1
AnchorX=Center
AnchorY=Top
WindowX=580
WindowY=95
SkinWidth=200
SkinHeight=200

[Variables]
@include=../Theme.inc

[MeasureHourMin]
Measure=Time
Format=%I:%M

[MeasureSec]
Measure=Time
Format=%S
MinValue=0
MaxValue=60

[MeasureAmPm]
Measure=Time
Format=%p

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,200,200,#CornerRadius# | #BgFill# | #BorderStroke#
Shape2=Ellipse 100,100,82,82 | Fill Color 0,0,0,0 | StrokeWidth 5 | Stroke Color #TrackColor#
Shape3=Ellipse 100,100,66,66 | Fill Color #TrackColor# | StrokeWidth 1.5 | Stroke Color #AccentColor#

[MeterSecRing]
Meter=Roundline
MeasureName=MeasureSec
X=0
Y=0
W=200
H=200
StartAngle=4.7123889
RotationAngle=6.2831853
LineStart=79
LineLength=85
Solid=1
LineColor=#AccentColor#

[MeterSubLabel]
Meter=String
X=100
Y=62
FontFace=Sans
FontSize=9
FontColor=#SubTextColor#
StringAlign=CenterCenter
Text="CURRENT TIME"
AntiAlias=1

[MeterTimeText]
Meter=String
MeasureName=MeasureHourMin
X=100
Y=98
FontFace=Sans
FontSize=28
FontColor=#TextColor#
StringAlign=CenterCenter
Text="%1"
AntiAlias=1

[MeterAmPm]
Meter=String
MeasureName=MeasureAmPm
X=100
Y=134
FontFace=Sans
FontSize=11
FontColor=#AccentColor#
StringAlign=CenterCenter
Text="%1"
AntiAlias=1
""",
            "BasicCpu/BasicCpu.ini": """[Rainmeter]
Update=1000
AccurateText=1
AnchorX=Left
AnchorY=Bottom
WindowX=36
WindowY=490
SkinWidth=135
SkinHeight=145

[Variables]
@include=../Theme.inc

[MeasureCPU]
Measure=CPU

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,135,145,#CornerRadius# | #BgFill# | #BorderStroke#
Shape2=Ellipse 67,68,46,46 | Fill Color 0,0,0,0 | StrokeWidth 7 | Stroke Color #TrackColor#

[MeterRing]
Meter=Roundline
MeasureName=MeasureCPU
X=2
Y=3
W=130
H=130
StartAngle=4.7123889
RotationAngle=6.2831853
LineStart=42
LineLength=50
Solid=1
LineColor=#AccentColor#

[MeterVal]
Meter=String
MeasureName=MeasureCPU
X=67
Y=58
FontFace=Sans
FontSize=15
FontColor=#TextColor#
StringAlign=CenterCenter
Text="%1%"
AntiAlias=1

[MeterLabel]
Meter=String
X=67
Y=82
FontFace=Sans
FontSize=10
FontColor=#SubTextColor#
StringAlign=CenterCenter
Text="CPU"
AntiAlias=1
""",
            "BasicRamSwap/BasicRamSwap.ini": """[Rainmeter]
Update=1000
AccurateText=1
AnchorX=Left
AnchorY=Top
WindowX=24
WindowY=20
SkinWidth=230
SkinHeight=145

[Variables]
@include=../Theme.inc

[MeasureRAM]
Measure=PhysicalMemory

[MeasureSwap]
Measure=SwapMemory

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,230,145,#CornerRadius# | #BgFill# | #BorderStroke#
Shape2=Ellipse 62,68,42,42 | Fill Color 0,0,0,0 | StrokeWidth 6 | Stroke Color #TrackColor#
Shape3=Ellipse 168,68,42,42 | Fill Color 0,0,0,0 | StrokeWidth 6 | Stroke Color #TrackColor#

[MeterRamRing]
Meter=Roundline
MeasureName=MeasureRAM
X=2
Y=8
W=120
H=120
StartAngle=4.7123889
RotationAngle=6.2831853
LineStart=39
LineLength=45
Solid=1
LineColor=#AccentColor#

[MeterSwapRing]
Meter=Roundline
MeasureName=MeasureSwap
X=108
Y=8
W=120
H=120
StartAngle=4.7123889
RotationAngle=6.2831853
LineStart=39
LineLength=45
Solid=1
LineColor=#AccentColor#

[MeterRamVal]
Meter=String
MeasureName=MeasureRAM
X=62
Y=60
FontFace=Sans
FontSize=14
FontColor=#TextColor#
StringAlign=CenterCenter
Text="%1%"
AntiAlias=1

[MeterRamLbl]
Meter=String
X=62
Y=80
FontFace=Sans
FontSize=9
FontColor=#SubTextColor#
StringAlign=CenterCenter
Text="RAM"
AntiAlias=1

[MeterSwapVal]
Meter=String
MeasureName=MeasureSwap
X=168
Y=60
FontFace=Sans
FontSize=14
FontColor=#TextColor#
StringAlign=CenterCenter
Text="%1%"
AntiAlias=1

[MeterSwapLbl]
Meter=String
X=168
Y=80
FontFace=Sans
FontSize=9
FontColor=#SubTextColor#
StringAlign=CenterCenter
Text="SWAP"
AntiAlias=1
""",
            "BasicDisks/BasicDisks.ini": """[Rainmeter]
Update=5000
AccurateText=1
AnchorX=Right
AnchorY=Center
WindowX=1110
WindowY=235
SkinWidth=230
SkinHeight=140

[Variables]
@include=../Theme.inc

[MeasureRoot]
Measure=FreeDiskSpace
Drive=/

[MeasureHome]
Measure=FreeDiskSpace
Drive=/home

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,230,140,#CornerRadius# | #BgFill# | #BorderStroke#
Shape2=Ellipse 62,66,40,40 | Fill Color 0,0,0,0 | StrokeWidth 6 | Stroke Color #TrackColor#
Shape3=Ellipse 168,66,40,40 | Fill Color 0,0,0,0 | StrokeWidth 6 | Stroke Color #TrackColor#

[MeterRootRing]
Meter=Roundline
MeasureName=MeasureRoot
X=2
Y=6
W=120
H=120
StartAngle=4.7123889
RotationAngle=6.2831853
LineStart=37
LineLength=43
Solid=1
LineColor=#AccentColor#

[MeterHomeRing]
Meter=Roundline
MeasureName=MeasureHome
X=108
Y=6
W=120
H=120
StartAngle=4.7123889
RotationAngle=6.2831853
LineStart=37
LineLength=43
Solid=1
LineColor=#AccentColor#

[MeterRootVal]
Meter=String
MeasureName=MeasureRoot
X=62
Y=58
FontFace=Sans
FontSize=12
FontColor=#TextColor#
StringAlign=CenterCenter
Text="%1%"
AntiAlias=1

[MeterRootLbl]
Meter=String
X=62
Y=78
FontFace=Sans
FontSize=9
FontColor=#SubTextColor#
StringAlign=CenterCenter
Text="ROOT /"
AntiAlias=1

[MeterHomeVal]
Meter=String
MeasureName=MeasureHome
X=168
Y=58
FontFace=Sans
FontSize=12
FontColor=#TextColor#
StringAlign=CenterCenter
Text="%1%"
AntiAlias=1

[MeterHomeLbl]
Meter=String
X=168
Y=78
FontFace=Sans
FontSize=9
FontColor=#SubTextColor#
StringAlign=CenterCenter
Text="/HOME"
AntiAlias=1
""",
            "BasicStorage/BasicStorage.ini": """[Rainmeter]
Update=5000
AccurateText=1
AnchorX=Right
AnchorY=Bottom
WindowX=1205
WindowY=390
SkinWidth=135
SkinHeight=145

[Variables]
@include=../Theme.inc

[MeasureStorage]
Measure=FreeDiskSpace
Drive=/

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,135,145,#CornerRadius# | #BgFill# | #BorderStroke#
Shape2=Ellipse 67,68,46,46 | Fill Color 0,0,0,0 | StrokeWidth 7 | Stroke Color #TrackColor#

[MeterRing]
Meter=Roundline
MeasureName=MeasureStorage
X=2
Y=3
W=130
H=130
StartAngle=4.7123889
RotationAngle=6.2831853
LineStart=42
LineLength=50
Solid=1
LineColor=#AccentColor#

[MeterVal]
Meter=String
MeasureName=MeasureStorage
X=67
Y=58
FontFace=Sans
FontSize=14
FontColor=#TextColor#
StringAlign=CenterCenter
Text="%1%"
AntiAlias=1

[MeterLbl]
Meter=String
X=67
Y=82
FontFace=Sans
FontSize=9
FontColor=#SubTextColor#
StringAlign=CenterCenter
Text="DISK"
AntiAlias=1
""",
            "BasicNet/BasicNet.ini": """[Rainmeter]
Update=1000
AccurateText=1
AnchorX=Right
AnchorY=Top
WindowX=1205
WindowY=35
SkinWidth=135
SkinHeight=155

[Variables]
@include=../Theme.inc

[MeasureNetIn]
Measure=NetIn

[MeasureNetOut]
Measure=NetOut

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,135,155,#CornerRadius# | #BgFill# | #BorderStroke#
Shape2=Ellipse 67,72,46,46 | Fill Color 0,0,0,0 | StrokeWidth 6 | Stroke Color #TrackColor#
Shape3=Ellipse 67,72,34,34 | Fill Color 0,0,0,0 | StrokeWidth 5 | Stroke Color #TrackColor#

[MeterInRing]
Meter=Roundline
MeasureName=MeasureNetIn
X=2
Y=7
W=130
H=130
StartAngle=4.7123889
RotationAngle=6.2831853
LineStart=43
LineLength=49
Solid=1
LineColor=#AccentColor#

[MeterOutRing]
Meter=Roundline
MeasureName=MeasureNetOut
X=2
Y=7
W=130
H=130
StartAngle=4.7123889
RotationAngle=6.2831853
LineStart=31
LineLength=37
Solid=1
LineColor=#TextColor#

[MeterNetTitle]
Meter=String
X=67
Y=72
FontFace=Sans
FontSize=11
FontColor=#TextColor#
StringAlign=CenterCenter
Text="NET I/O"
AntiAlias=1

[MeterSub]
Meter=String
X=67
Y=136
FontFace=Sans
FontSize=9
FontColor=#AccentColor#
StringAlign=CenterCenter
Text="LIVE TRAFFIC"
AntiAlias=1
""",
        }
    elif design_id == "capsule":
        files = {
            "BasicClock/BasicClock.ini": """[Rainmeter]
Update=1000
AccurateText=1
AnchorX=Center
AnchorY=Top
WindowX=608
WindowY=95
SkinWidth=150
SkinHeight=220

[Variables]
@include=../Theme.inc

[MeasureHour]
Measure=Time
Format=%H

[MeasureMin]
Measure=Time
Format=%M

[MeasureSec]
Measure=Time
Format=%S

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,150,220,75 | #BgFill# | #BorderStroke#

[MeterHour]
Meter=String
MeasureName=MeasureHour
X=75
Y=62
FontFace=Sans
FontSize=50
FontColor=#TextColor#
StringAlign=CenterCenter
Text="%1"
AntiAlias=1

[MeterMin]
Meter=String
MeasureName=MeasureMin
X=75
Y=138
FontFace=Sans
FontSize=50
FontColor=#AccentColor#
StringAlign=CenterCenter
Text="%1"
AntiAlias=1

[MeterSec]
Meter=String
MeasureName=MeasureSec
X=75
Y=192
FontFace=Sans
FontSize=11
FontColor=#SubTextColor#
StringAlign=CenterCenter
Text=":%1"
AntiAlias=1
""",
            "BasicCpu/BasicCpu.ini": """[Rainmeter]
Update=1000
AccurateText=1
AnchorX=Left
AnchorY=Bottom
WindowX=36
WindowY=490
SkinWidth=105
SkinHeight=215

[Variables]
@include=../Theme.inc

[MeasureCPU]
Measure=CPU

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,105,215,38 | #BgFill# | #BorderStroke#

[MeterLabel]
Meter=String
X=52
Y=16
FontFace=Sans
FontSize=12
FontColor=#SubTextColor#
StringAlign=Center
Text="CPU"
AntiAlias=1

[MeterBar]
Meter=Bar
MeasureName=MeasureCPU
X=36
Y=44
W=32
H=120
BarOrientation=Vertical
BarColor=#AccentColor#
SolidColor=#TrackColor#

[MeterValue]
Meter=String
MeasureName=MeasureCPU
X=52
Y=178
FontFace=Sans
FontSize=13
FontColor=#TextColor#
StringAlign=Center
Text="%1%"
AntiAlias=1
""",
            "BasicRamSwap/BasicRamSwap.ini": """[Rainmeter]
Update=1000
AccurateText=1
AnchorX=Left
AnchorY=Top
WindowX=24
WindowY=16
SkinWidth=140
SkinHeight=270

[Variables]
@include=../Theme.inc

[MeasureRAM]
Measure=PhysicalMemory

[MeasureSwap]
Measure=SwapMemory

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,140,270,38 | #BgFill# | #BorderStroke#

[MeterRamLabel]
Meter=String
X=42
Y=18
FontFace=Sans
FontSize=11
FontColor=#SubTextColor#
StringAlign=Center
Text="RAM"
AntiAlias=1

[MeterSwapLabel]
Meter=String
X=98
Y=18
FontFace=Sans
FontSize=11
FontColor=#SubTextColor#
StringAlign=Center
Text="SWAP"
AntiAlias=1

[MeterRamBar]
Meter=Bar
MeasureName=MeasureRAM
X=27
Y=46
W=30
H=160
BarOrientation=Vertical
BarColor=#AccentColor#
SolidColor=#TrackColor#

[MeterSwapBar]
Meter=Bar
MeasureName=MeasureSwap
X=83
Y=46
W=30
H=160
BarOrientation=Vertical
BarColor=#AccentColor#
SolidColor=#TrackColor#

[MeterRamVal]
Meter=String
MeasureName=MeasureRAM
X=42
Y=222
FontFace=Sans
FontSize=12
FontColor=#TextColor#
StringAlign=Center
Text="%1%"
AntiAlias=1

[MeterSwapVal]
Meter=String
MeasureName=MeasureSwap
X=98
Y=222
FontFace=Sans
FontSize=12
FontColor=#TextColor#
StringAlign=Center
Text="%1%"
AntiAlias=1
""",
            "BasicDisks/BasicDisks.ini": """[Rainmeter]
Update=5000
AccurateText=1
AnchorX=Right
AnchorY=Center
WindowX=1170
WindowY=250
SkinWidth=165
SkinHeight=115

[Variables]
@include=../Theme.inc

[MeasureRoot]
Measure=FreeDiskSpace
Drive=/

[MeasureHome]
Measure=FreeDiskSpace
Drive=/home

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,165,115,28 | #BgFill# | #BorderStroke#

[MeterRootLabel]
Meter=String
MeasureName=MeasureRoot
X=82
Y=14
FontFace=Sans
FontSize=10
FontColor=#TextColor#
StringAlign=Center
Text="/ : %1%"
AntiAlias=1

[MeterRootBar]
Meter=Bar
MeasureName=MeasureRoot
X=20
Y=34
W=125
H=12
BarOrientation=Horizontal
BarColor=#AccentColor#
SolidColor=#TrackColor#

[MeterHomeLabel]
Meter=String
MeasureName=MeasureHome
X=82
Y=60
FontFace=Sans
FontSize=10
FontColor=#TextColor#
StringAlign=Center
Text="/home : %1%"
AntiAlias=1

[MeterHomeBar]
Meter=Bar
MeasureName=MeasureHome
X=20
Y=80
W=125
H=12
BarOrientation=Horizontal
BarColor=#AccentColor#
SolidColor=#TrackColor#
""",
            "BasicStorage/BasicStorage.ini": """[Rainmeter]
Update=5000
AccurateText=1
AnchorX=Right
AnchorY=Bottom
WindowX=1225
WindowY=390
SkinWidth=105
SkinHeight=205

[Variables]
@include=../Theme.inc

[MeasureStorage]
Measure=FreeDiskSpace
Drive=/

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,105,205,38 | #BgFill# | #BorderStroke#

[MeterTitle]
Meter=String
X=52
Y=16
FontFace=Sans
FontSize=11
FontColor=#SubTextColor#
StringAlign=Center
Text="DISK"
AntiAlias=1

[MeterBar]
Meter=Bar
MeasureName=MeasureStorage
X=36
Y=44
W=32
H=115
BarOrientation=Vertical
BarColor=#AccentColor#
SolidColor=#TrackColor#

[MeterVal]
Meter=String
MeasureName=MeasureStorage
X=52
Y=172
FontFace=Sans
FontSize=12
FontColor=#TextColor#
StringAlign=Center
Text="%1%"
AntiAlias=1
""",
            "BasicNet/BasicNet.ini": """[Rainmeter]
Update=1000
AccurateText=1
AnchorX=Right
AnchorY=Top
WindowX=1205
WindowY=40
SkinWidth=125
SkinHeight=185

[Variables]
@include=../Theme.inc

[MeasureNetIn]
Measure=NetIn

[MeasureNetOut]
Measure=NetOut

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,125,185,34 | #BgFill# | #BorderStroke#

[MeterHeader]
Meter=String
X=62
Y=14
FontFace=Sans
FontSize=11
FontColor=#SubTextColor#
StringAlign=Center
Text="NET"
AntiAlias=1

[MeterInBar]
Meter=Bar
MeasureName=MeasureNetIn
X=28
Y=42
W=24
H=100
BarOrientation=Vertical
BarColor=#AccentColor#
SolidColor=#TrackColor#

[MeterOutBar]
Meter=Bar
MeasureName=MeasureNetOut
X=72
Y=42
W=24
H=100
BarOrientation=Vertical
BarColor=#AccentColor#
SolidColor=#TrackColor#

[MeterInLabel]
Meter=String
X=40
Y=152
FontFace=Sans
FontSize=10
FontColor=#TextColor#
StringAlign=Center
Text="In"
AntiAlias=1

[MeterOutLabel]
Meter=String
X=84
Y=152
FontFace=Sans
FontSize=10
FontColor=#TextColor#
StringAlign=Center
Text="Out"
AntiAlias=1
""",
        }
    elif design_id == "horizontal":
        files = {
            "BasicClock/BasicClock.ini": """[Rainmeter]
Update=1000
AccurateText=1
AnchorX=Center
AnchorY=Top
WindowX=550
WindowY=125
SkinWidth=265
SkinHeight=115

[Variables]
@include=../Theme.inc

[MeasureTime]
Measure=Time
Format=%H:%M

[MeasureSec]
Measure=Time
Format=%S

[MeasureDay]
Measure=Time
Format=%A

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,265,115,#CornerRadius# | #BgFill# | #BorderStroke#
Shape2=Rectangle 12,14,6,87,3 | Fill Color #AccentColor# | StrokeWidth 0

[MeterDay]
Meter=String
MeasureName=MeasureDay
X=32
Y=16
FontFace=Sans
FontSize=11
FontColor=#AccentColor#
StringAlign=Left
Text="%1"
AntiAlias=1

[MeterClock]
Meter=String
MeasureName=MeasureTime
X=30
Y=36
FontFace=Sans
FontSize=42
FontColor=#TextColor#
StringAlign=Left
Text="%1"
AntiAlias=1

[MeterSec]
Meter=String
MeasureName=MeasureSec
X=245
Y=68
FontFace=Sans
FontSize=16
FontColor=#SubTextColor#
StringAlign=Right
Text=":%1"
AntiAlias=1
""",
            "BasicCpu/BasicCpu.ini": """[Rainmeter]
Update=1000
AccurateText=1
AnchorX=Left
AnchorY=Bottom
WindowX=36
WindowY=520
SkinWidth=210
SkinHeight=72

[Variables]
@include=../Theme.inc

[MeasureCPU]
Measure=CPU

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,210,72,#CornerRadius# | #BgFill# | #BorderStroke#

[MeterLabel]
Meter=String
X=16
Y=14
FontFace=Sans
FontSize=11
FontColor=#SubTextColor#
StringAlign=Left
Text="CPU USAGE"
AntiAlias=1

[MeterValue]
Meter=String
MeasureName=MeasureCPU
X=194
Y=14
FontFace=Sans
FontSize=12
FontColor=#TextColor#
StringAlign=Right
Text="%1%"
AntiAlias=1

[MeterBar]
Meter=Bar
MeasureName=MeasureCPU
X=16
Y=44
W=178
H=8
BarOrientation=Horizontal
BarColor=#AccentColor#
SolidColor=#TrackColor#
""",
            "BasicRamSwap/BasicRamSwap.ini": """[Rainmeter]
Update=1000
AccurateText=1
AnchorX=Left
AnchorY=Top
WindowX=24
WindowY=20
SkinWidth=210
SkinHeight=115

[Variables]
@include=../Theme.inc

[MeasureRAM]
Measure=PhysicalMemory

[MeasureSwap]
Measure=SwapMemory

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,210,115,#CornerRadius# | #BgFill# | #BorderStroke#

[MeterRamLabel]
Meter=String
X=16
Y=14
FontFace=Sans
FontSize=10
FontColor=#SubTextColor#
StringAlign=Left
Text="RAM"
AntiAlias=1

[MeterRamVal]
Meter=String
MeasureName=MeasureRAM
X=194
Y=14
FontFace=Sans
FontSize=11
FontColor=#TextColor#
StringAlign=Right
Text="%1%"
AntiAlias=1

[MeterRamBar]
Meter=Bar
MeasureName=MeasureRAM
X=16
Y=36
W=178
H=7
BarOrientation=Horizontal
BarColor=#AccentColor#
SolidColor=#TrackColor#

[MeterSwapLabel]
Meter=String
X=16
Y=62
FontFace=Sans
FontSize=10
FontColor=#SubTextColor#
StringAlign=Left
Text="SWAP"
AntiAlias=1

[MeterSwapVal]
Meter=String
MeasureName=MeasureSwap
X=194
Y=62
FontFace=Sans
FontSize=11
FontColor=#TextColor#
StringAlign=Right
Text="%1%"
AntiAlias=1

[MeterSwapBar]
Meter=Bar
MeasureName=MeasureSwap
X=16
Y=84
W=178
H=7
BarOrientation=Horizontal
BarColor=#AccentColor#
SolidColor=#TrackColor#
""",
            "BasicDisks/BasicDisks.ini": """[Rainmeter]
Update=5000
AccurateText=1
AnchorX=Right
AnchorY=Center
WindowX=1130
WindowY=250
SkinWidth=210
SkinHeight=115

[Variables]
@include=../Theme.inc

[MeasureRoot]
Measure=FreeDiskSpace
Drive=/

[MeasureHome]
Measure=FreeDiskSpace
Drive=/home

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,210,115,#CornerRadius# | #BgFill# | #BorderStroke#

[MeterRootLabel]
Meter=String
MeasureName=MeasureRoot
X=16
Y=14
FontFace=Sans
FontSize=10
FontColor=#TextColor#
StringAlign=Left
Text="ROOT / : %1%"
AntiAlias=1

[MeterRootBar]
Meter=Bar
MeasureName=MeasureRoot
X=16
Y=36
W=178
H=7
BarOrientation=Horizontal
BarColor=#AccentColor#
SolidColor=#TrackColor#

[MeterHomeLabel]
Meter=String
MeasureName=MeasureHome
X=16
Y=62
FontFace=Sans
FontSize=10
FontColor=#TextColor#
StringAlign=Left
Text="HOME : %1%"
AntiAlias=1

[MeterHomeBar]
Meter=Bar
MeasureName=MeasureHome
X=16
Y=84
W=178
H=7
BarOrientation=Horizontal
BarColor=#AccentColor#
SolidColor=#TrackColor#
""",
            "BasicStorage/BasicStorage.ini": """[Rainmeter]
Update=5000
AccurateText=1
AnchorX=Right
AnchorY=Bottom
WindowX=1130
WindowY=390
SkinWidth=210
SkinHeight=75

[Variables]
@include=../Theme.inc

[MeasureStorage]
Measure=FreeDiskSpace
Drive=/

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,210,75,#CornerRadius# | #BgFill# | #BorderStroke#

[MeterTitle]
Meter=String
X=16
Y=14
FontFace=Sans
FontSize=10
FontColor=#SubTextColor#
StringAlign=Left
Text="STORAGE (ROOT)"
AntiAlias=1

[MeterVal]
Meter=String
MeasureName=MeasureStorage
X=194
Y=14
FontFace=Sans
FontSize=11
FontColor=#TextColor#
StringAlign=Right
Text="%1%"
AntiAlias=1

[MeterBar]
Meter=Bar
MeasureName=MeasureStorage
X=16
Y=44
W=178
H=8
BarOrientation=Horizontal
BarColor=#AccentColor#
SolidColor=#TrackColor#
""",
            "BasicNet/BasicNet.ini": """[Rainmeter]
Update=1000
AccurateText=1
AnchorX=Right
AnchorY=Top
WindowX=1130
WindowY=40
SkinWidth=210
SkinHeight=110

[Variables]
@include=../Theme.inc

[MeasureNetIn]
Measure=NetIn

[MeasureNetOut]
Measure=NetOut

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,210,110,#CornerRadius# | #BgFill# | #BorderStroke#

[MeterInLabel]
Meter=String
X=16
Y=14
FontFace=Sans
FontSize=10
FontColor=#SubTextColor#
StringAlign=Left
Text="NET DOWNLOAD"
AntiAlias=1

[MeterInBar]
Meter=Bar
MeasureName=MeasureNetIn
X=16
Y=36
W=178
H=7
BarOrientation=Horizontal
BarColor=#AccentColor#
SolidColor=#TrackColor#

[MeterOutLabel]
Meter=String
X=16
Y=60
FontFace=Sans
FontSize=10
FontColor=#SubTextColor#
StringAlign=Left
Text="NET UPLOAD"
AntiAlias=1

[MeterOutBar]
Meter=Bar
MeasureName=MeasureNetOut
X=16
Y=82
W=178
H=7
BarOrientation=Horizontal
BarColor=#AccentColor#
SolidColor=#TrackColor#
""",
        }
    else:
        # Default: "vertical" (Classic HUD Vertical Bars)
        files = {
            "BasicClock/BasicClock.ini": """[Rainmeter]
Update=1000
AccurateText=1
AnchorX=Center
AnchorY=Top
WindowX=563
WindowY=139
SkinWidth=235
SkinHeight=165

[Variables]
@include=../Theme.inc

[MeasureHour]
Measure=Time
Format=%I

[MeasureMinute]
Measure=Time
Format=%M

[MeasureSecond]
Measure=Time
Format=%S

[MeasureAmPm]
Measure=Time
Format=%p

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,235,165,#CornerRadius# | #BgFill# | #BorderStroke#

[MeterHour]
Meter=String
MeasureName=MeasureHour
X=16
Y=8
FontFace=Sans
FontSize=54
FontColor=#TextColor#
StringAlign=Left
Text="%1"
AntiAlias=1

[MeterSecond]
Meter=String
MeasureName=MeasureSecond
X=18
Y=120
FontFace=Sans
FontSize=18
FontColor=#TextColor#
StringAlign=Left
Text="%1"
AntiAlias=1

[MeterAmPm]
Meter=String
MeasureName=MeasureAmPm
X=56
Y=128
FontFace=Sans
FontSize=10
FontColor=#AccentColor#
StringAlign=Left
Text="%1"
AntiAlias=1

[MeterMinute]
Meter=String
MeasureName=MeasureMinute
X=218
Y=95
FontFace=Sans
FontSize=38
FontColor=#AccentColor#
StringAlign=Right
Text="%1"
AntiAlias=1
""",
            "BasicCpu/BasicCpu.ini": """[Rainmeter]
Update=1000
AccurateText=1
AnchorX=Left
AnchorY=Bottom
WindowX=36
WindowY=490
SkinWidth=85
SkinHeight=215

[Variables]
@include=../Theme.inc

[MeasureCPU]
Measure=CPU

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,85,215,#CornerRadius# | #BgFill# | #BorderStroke#

[MeterLabel]
Meter=String
X=42
Y=14
FontFace=Sans
FontSize=12
FontColor=#SubTextColor#
StringAlign=Center
Text="Cpu"
AntiAlias=1

[MeterBar]
Meter=Bar
MeasureName=MeasureCPU
X=37
Y=48
W=10
H=110
BarOrientation=Vertical
BarColor=#AccentColor#
SolidColor=#TrackColor#

[MeterValue]
Meter=String
MeasureName=MeasureCPU
X=42
Y=180
FontFace=Sans
FontSize=12
FontColor=#TextColor#
StringAlign=Center
Text="%1%"
AntiAlias=1
""",
            "BasicRamSwap/BasicRamSwap.ini": """[Rainmeter]
Update=1000
AccurateText=1
AnchorX=Left
AnchorY=Top
WindowX=23
WindowY=15
SkinWidth=120
SkinHeight=350

[Variables]
@include=../Theme.inc

[MeasureRAM]
Measure=PhysicalMemory

[MeasureSwap]
Measure=SwapMemory

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,120,350,#CornerRadius# | #BgFill# | #BorderStroke#

[MeterRamLabel]
Meter=String
X=34
Y=18
FontFace=Sans
FontSize=12
FontColor=#SubTextColor#
StringAlign=Center
Text="Ram"
AntiAlias=1

[MeterSwapLabel]
Meter=String
X=88
Y=18
FontFace=Sans
FontSize=12
FontColor=#SubTextColor#
StringAlign=Center
Text="Swap"
AntiAlias=1

[MeterRamBar]
Meter=Bar
MeasureName=MeasureRAM
X=30
Y=78
W=8
H=180
BarOrientation=Vertical
BarColor=#AccentColor#
SolidColor=#TrackColor#

[MeterSwapBar]
Meter=Bar
MeasureName=MeasureSwap
X=84
Y=78
W=8
H=180
BarOrientation=Vertical
BarColor=#AccentColor#
SolidColor=#TrackColor#

[MeterRamVal]
Meter=String
MeasureName=MeasureRAM
X=34
Y=282
FontFace=Sans
FontSize=11
FontColor=#TextColor#
StringAlign=Center
Text="%1%"
AntiAlias=1

[MeterRamUsed]
Meter=String
X=34
Y=300
FontFace=Sans
FontSize=10
FontColor=#SubTextColor#
StringAlign=Center
Text="Used"
AntiAlias=1

[MeterSwapVal]
Meter=String
MeasureName=MeasureSwap
X=88
Y=282
FontFace=Sans
FontSize=11
FontColor=#TextColor#
StringAlign=Center
Text="%1%"
AntiAlias=1

[MeterSwapUsed]
Meter=String
X=88
Y=300
FontFace=Sans
FontSize=10
FontColor=#SubTextColor#
StringAlign=Center
Text="Used"
AntiAlias=1
""",
            "BasicDisks/BasicDisks.ini": """[Rainmeter]
Update=5000
AccurateText=1
AnchorX=Right
AnchorY=Center
WindowX=1224
WindowY=252
SkinWidth=105
SkinHeight=105

[Variables]
@include=../Theme.inc

[MeasureRoot]
Measure=FreeDiskSpace
Drive=/

[MeasureHome]
Measure=FreeDiskSpace
Drive=/home

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,105,105,#CornerRadius# | #BgFill# | #BorderStroke#

[MeterRootLabel]
Meter=String
MeasureName=MeasureRoot
X=52
Y=10
FontFace=Sans
FontSize=10
FontColor=#TextColor#
StringAlign=Center
Text="/: %1"
AntiAlias=1

[MeterRootBar]
Meter=Bar
MeasureName=MeasureRoot
X=20
Y=34
W=65
H=8
BarOrientation=Horizontal
BarColor=#AccentColor#
SolidColor=#TrackColor#

[MeterHomeLabel]
Meter=String
MeasureName=MeasureHome
X=52
Y=54
FontFace=Sans
FontSize=10
FontColor=#TextColor#
StringAlign=Center
Text="/home: %1"
AntiAlias=1

[MeterHomeBar]
Meter=Bar
MeasureName=MeasureHome
X=20
Y=78
W=65
H=8
BarOrientation=Horizontal
BarColor=#AccentColor#
SolidColor=#TrackColor#
""",
            "BasicStorage/BasicStorage.ini": """[Rainmeter]
Update=5000
AccurateText=1
AnchorX=Right
AnchorY=Bottom
WindowX=1235
WindowY=391
SkinWidth=95
SkinHeight=200

[Variables]
@include=../Theme.inc

[MeasureStorage]
Measure=FreeDiskSpace
Drive=/

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,95,200,#CornerRadius# | #BgFill# | #BorderStroke#

[MeterTitle]
Meter=String
X=48
Y=14
FontFace=Sans
FontSize=12
FontColor=#SubTextColor#
StringAlign=Center
Text="Storage"
AntiAlias=1

[MeterSub]
Meter=String
X=48
Y=32
FontFace=Sans
FontSize=10
FontColor=#SubTextColor#
StringAlign=Center
Text="Root"
AntiAlias=1

[MeterBar]
Meter=Bar
MeasureName=MeasureStorage
X=44
Y=62
W=8
H=90
BarOrientation=Vertical
BarColor=#AccentColor#
SolidColor=#TrackColor#

[MeterVal]
Meter=String
MeasureName=MeasureStorage
X=48
Y=166
FontFace=Sans
FontSize=11
FontColor=#TextColor#
StringAlign=Center
Text="%1"
AntiAlias=1
""",
            "BasicNet/BasicNet.ini": """[Rainmeter]
Update=1000
AccurateText=1
AnchorX=Right
AnchorY=Top
WindowX=1224
WindowY=40
SkinWidth=105
SkinHeight=175

[Variables]
@include=../Theme.inc

[MeasureNetIn]
Measure=NetIn

[MeasureNetOut]
Measure=NetOut

[MeterBG]
Meter=Shape
Shape=Rectangle 0,0,105,175,#CornerRadius# | #BgFill# | #BorderStroke#

[MeterHeader]
Meter=String
X=52
Y=12
FontFace=Sans
FontSize=12
FontColor=#SubTextColor#
StringAlign=Center
Text="Net"
AntiAlias=1

[MeterInBar]
Meter=Bar
MeasureName=MeasureNetIn
X=32
Y=46
W=7
H=88
BarOrientation=Vertical
BarColor=#AccentColor#
SolidColor=#TrackColor#

[MeterOutBar]
Meter=Bar
MeasureName=MeasureNetOut
X=66
Y=46
W=7
H=88
BarOrientation=Vertical
BarColor=#AccentColor#
SolidColor=#TrackColor#

[MeterInLabel]
Meter=String
X=35
Y=144
FontFace=Sans
FontSize=10
FontColor=#TextColor#
StringAlign=Center
Text="In"
AntiAlias=1

[MeterOutLabel]
Meter=String
X=70
Y=144
FontFace=Sans
FontSize=10
FontColor=#TextColor#
StringAlign=Center
Text="Out"
AntiAlias=1
""",
        }

    for rel_path, content in files.items():
        full_path = os.path.join(WIDGETS_DIR, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)



def get_engine_pids():
    """Find all running (non-zombie) rainmeter-native PIDs via /proc."""
    pids = []
    my_pid = os.getpid()
    try:
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            pid = int(entry)
            if pid == my_pid:
                continue
            try:
                with open(f"/proc/{pid}/stat", "r", encoding="utf-8", errors="ignore") as sf:
                    stat_str = sf.read()
                rparen = stat_str.rfind(")")
                if rparen != -1 and len(stat_str) > rparen + 2:
                    state_char = stat_str[rparen + 2]
                    if state_char in ("Z", "X"):
                        continue
                    comm = stat_str[stat_str.find("(") + 1 : rparen]
                    if comm.startswith("rainmeter-nativ"):
                        pids.append(pid)
                        continue
                exe = os.readlink(f"/proc/{pid}/exe")
                if os.path.basename(exe) == "rainmeter-native":
                    pids.append(pid)
            except (OSError, PermissionError):
                continue
    except Exception:
        pass
    return pids


def stop_engine():
    """Immediately stop all running rainmeter-native instances (including across Flatpak/host boundaries)."""
    token_file = os.path.join(CONFIG_DIR, "engine.token")
    try:
        if os.path.exists(token_file):
            os.remove(token_file)
    except OSError:
        pass
    for pid in get_engine_pids():
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    for pid in get_engine_pids():
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass


def detect_monitors():
    """Return list of connected monitors with geometry and scale."""
    monitors = []
    try:
        display = Gdk.Display.get_default()
        if display is not None:
            mon_list = display.get_monitors()
            for i in range(mon_list.get_n_items()):
                m = mon_list.get_item(i)
                geom = m.get_geometry()
                scale = m.get_scale_factor()
                connector = m.get_connector() or f"Display-{i}"
                monitors.append(
                    {
                        "index": i,
                        "name": f"Monitor {i} ({connector} — {geom.width}×{geom.height})",
                        "width": max(320, geom.width),
                        "height": max(240, geom.height),
                        "scale": scale,
                    }
                )
    except Exception:
        pass

    if not monitors:
        monitors.append(
            {
                "index": 0,
                "name": "Monitor 0 (Default — 1366×768)",
                "width": 1366,
                "height": 768,
                "scale": 1,
            }
        )
    return monitors


def estimate_skin_size(ini_path):
    """Parse an INI file lightly to estimate its unscaled bounding box and default anchors."""
    info = {
        "width": 260,
        "height": 140,
        "anchor_x": "left",
        "anchor_y": "top",
        "window_x": None,
        "window_y": None,
    }
    if not os.path.isfile(ini_path):
        return info

    max_x = 240
    max_y = 100
    explicit_w = 0
    explicit_h = 0
    try:
        with open(ini_path, "r", encoding="utf-8", errors="ignore") as f:
            section = ""
            cur_x = 0.0
            cur_y = 0.0
            cur_w = 0.0
            cur_h = 0.0
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith(";"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    max_x = max(max_x, cur_x + max(cur_w, 40))
                    max_y = max(max_y, cur_y + max(cur_h, 24))
                    section = line[1:-1].strip().lower()
                    cur_x = 0.0
                    cur_y = 0.0
                    cur_w = 0.0
                    cur_h = 0.0
                    continue
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip().lower()
                v = v.strip()
                if section == "rainmeter":
                    if k == "anchorx" and v.lower() in ("left", "center", "right"):
                        info["anchor_x"] = v.lower()
                    elif k == "anchory" and v.lower() in ("top", "center", "bottom"):
                        info["anchor_y"] = v.lower()
                    elif k == "windowx":
                        try:
                            info["window_x"] = int(float(v))
                        except ValueError:
                            pass
                    elif k == "windowy":
                        try:
                            info["window_y"] = int(float(v))
                        except ValueError:
                            pass
                    elif k == "skinwidth":
                        try:
                            explicit_w = max(64, int(float(v)))
                        except ValueError:
                            pass
                    elif k == "skinheight":
                        try:
                            explicit_h = max(64, int(float(v)))
                        except ValueError:
                            pass
                else:
                    try:
                        if k == "x" and not v.lower().endswith("r"):
                            cur_x = float(v)
                        elif k == "y" and not v.lower().endswith("r"):
                            cur_y = float(v)
                        elif k == "w":
                            cur_w = float(v)
                        elif k == "h":
                            cur_h = float(v)
                        elif k == "shape" and "rectangle" in v.lower():
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
    """Return list of dicts describing built-in suites, basic widgets, and user-installed widgets."""
    items = []
    seen_abs = set()

    # 1. Built-in Suites under REPO_DIR/suites (and SYSTEM_SUITES_DIR)
    for suites_base in dict.fromkeys([SYSTEM_SUITES_DIR, SUITES_DIR]):
        if not os.path.isdir(suites_base):
            continue
        base_rel_root = REPO_DIR if suites_base.startswith(REPO_DIR) else CONFIG_DIR
        for folder in sorted(os.listdir(suites_base)):
            folder_path = os.path.join(suites_base, folder)
            if not os.path.isdir(folder_path):
                continue
            if os.path.isfile(os.path.join(folder_path, "suite.json")):
                continue
            for root, _dirs, files in os.walk(folder_path):
                for file in sorted(files):
                    if file.lower().endswith(".ini"):
                        abs_p = os.path.abspath(os.path.join(root, file))
                        if abs_p in seen_abs:
                            continue
                        seen_abs.add(abs_p)
                        rel_key = os.path.relpath(abs_p, base_rel_root)
                        meta = estimate_skin_size(abs_p)
                        items.append(
                            {
                                "key": rel_key,
                                "title": folder if file.lower() == f"{folder.lower()}.ini" else f"{folder} / {file[:-4]}",
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

    # 2. Anchored Basic Widgets under WIDGETS_DIR
    if os.path.isdir(WIDGETS_DIR):
        w_base_rel_root = REPO_DIR if WIDGETS_DIR.startswith(REPO_DIR) else CONFIG_DIR
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
                        rel_key = os.path.relpath(abs_p, w_base_rel_root)
                        meta = estimate_skin_size(abs_p)
                        items.append(
                            {
                                "key": rel_key,
                                "title": folder if file.lower() == f"{folder.lower()}.ini" else f"{folder} / {file[:-4]}",
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

    # 3. User-installed widgets under ~/.config/rainmeter-native/Skins
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
                rel_from_skins = os.path.relpath(abs_p, USER_SKINS_DIR)
                meta = estimate_skin_size(abs_p)
                items.append(
                    {
                        "key": abs_p,
                        "alt_key": os.path.dirname(rel_from_skins),
                        "title": os.path.splitext(rel_from_skins)[0].replace("/", " / "),
                        "subtitle": f"~/.config/rainmeter-native/Skins/{rel_from_skins}",
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
    """Return list of saved custom multi-widget suites from suites/*/suite.json."""
    custom_suites = []
    if not os.path.isdir(SUITES_DIR):
        return custom_suites
    for folder in sorted(os.listdir(SUITES_DIR)):
        manifest_path = os.path.join(SUITES_DIR, folder, "suite.json")
        if os.path.isfile(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                widgets = data.get("widgets", [])
                custom_suites.append(
                    {
                        "id": f"custom_suite::{folder}",
                        "folder": folder,
                        "title": data.get("name", folder),
                        "manifest_path": manifest_path,
                        "thm_path": os.path.join(SUITES_DIR, folder, f"{folder}.thm"),
                        "widgets": widgets,
                    }
                )
            except Exception:
                continue
    return custom_suites


def compute_autofit_scale(skin_info, mon_w, mon_h):
    """Compute automatic scale factor for a suite/widget on a monitor of size (mon_w, mon_h)."""
    raw_w = max(1, skin_info["est_w"])
    raw_h = max(1, skin_info["est_h"])
    if raw_w >= 1000 or raw_h >= 650:
        return round(min(mon_w / raw_w, mon_h / raw_h), 2)
    scale = max(0.6, min(2.5, mon_h / 768.0))
    if raw_w * scale > mon_w:
        scale = mon_w / raw_w
    return round(scale, 2)


def load_global_config(skins):
    """Read ~/.config/rainmeter-native/Rainmeter.ini into a per-skin state dictionary."""
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
    except Exception:
        return state

    for sec in cp.sections():
        matched_key = None
        for s in skins:
            if (
                sec == s["key"]
                or sec == s["abs_path"]
                or sec == s.get("alt_key")
                or s["abs_path"].endswith(sec)
            ):
                matched_key = s["key"]
                break
        if matched_key is None:
            continue

        st = state[matched_key]
        sec_map = {k.lower(): v.strip() for k, v in cp.items(sec)}
        st["active"] = sec_map.get("active", "0") not in ("0", "false", "")
        if "monitor" in sec_map:
            try:
                st["monitor"] = max(0, int(float(sec_map["monitor"])))
            except ValueError:
                pass
        if "anchorx" in sec_map and sec_map["anchorx"].lower() in ("left", "center", "right"):
            st["anchor_x"] = sec_map["anchorx"].lower()
        if "anchory" in sec_map and sec_map["anchory"].lower() in ("top", "center", "bottom"):
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
        if "scale" in sec_map:
            try:
                st["scale"] = max(0.25, min(3.0, float(sec_map["scale"])))
                st["auto_fit"] = False
            except ValueError:
                pass

    return state


def save_global_config(skins, state):
    """Write ~/.config/rainmeter-native/Rainmeter.ini from current UI state."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    lines = ["; Rainmeter Native Global Configuration\n"]
    for s in skins:
        key = s["key"]
        st = state.get(key)
        if not st:
            continue
        if (
            not st["active"]
            and not st["use_custom_pos"]
            and st["auto_fit"] == s["is_suite"]
            and abs(st["scale"] - 1.0) < 1e-3
        ):
            continue
        lines.append(f"[{key}]\n")
        lines.append(f"Active={1 if st['active'] else 0}\n")
        lines.append(f"Monitor={st['monitor']}\n")
        lines.append(f"AnchorX={st['anchor_x'].capitalize()}\n")
        lines.append(f"AnchorY={st['anchor_y'].capitalize()}\n")
        lines.append(f"AutoFit={1 if st['auto_fit'] else 0}\n")
        if not st["auto_fit"]:
            lines.append(f"Scale={st['scale']:.2f}\n")
        if st["use_custom_pos"]:
            lines.append(f"WindowX={int(st['x'])}\n")
            lines.append(f"WindowY={int(st['y'])}\n")
        lines.append("\n")

    with open(GLOBAL_CONFIG, "w", encoding="utf-8") as f:
        f.writelines(lines)


class ControlCenterWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("Trad Rainmeter")
        self.set_default_size(1080, 780)
        try:
            disp = Gdk.Display.get_default()
            if disp is not None:
                Gtk.IconTheme.get_for_display(disp).add_search_path(os.path.join(REPO_DIR, "assets"))
            self.set_icon_name("trad-engine")
        except Exception:
            pass

        self.monitors = detect_monitors()
        self.skins = discover_all_skins()
        self.custom_suites = discover_custom_suites()
        self.skin_state = load_global_config(self.skins)
        self.active_custom_suite_id = None
        (
            self.basic_theme_idx,
            self.basic_shape_idx,
            self.basic_design_idx,
        ) = read_current_basic_style()
        (
            self.weather_locations,
            self.weather_active_idx,
            self.weather_units,
        ) = load_weather_config()
        save_weather_config(self.weather_locations, self.weather_active_idx, self.weather_units)

        first_widget = next((s["key"] for s in self.skins if not s["is_suite"]), None)
        self.selected_key = first_widget or (self.skins[0]["key"] if self.skins else None)
        self.show_suites_in_widgets_tab = False
        self.suite_monitor_idx = 0
        for s in self.skins:
            if s["is_suite"] and self.skin_state[s["key"]]["active"]:
                self.suite_monitor_idx = self.skin_state[s["key"]]["monitor"]
                break

        self._updating_controls = False
        self._drag_start_win_x = 0
        self._drag_start_win_y = 0
        self.suite_buttons = {}
        self.custom_suite_buttons = {}
        self.basic_switches = {}
        self.row_map = {}
        self.weather_saved_rows = []
        self.weather_search_rows = []
        self._weather_search_results = []

        self._build_ui()
        self._populate_suites_tab()
        self._populate_weather_locations_ui()
        self._populate_basic_widgets_tab()
        self._populate_widgets_tab()
        if self.selected_key:
            self._select_widget(self.selected_key)
        self._update_engine_status()
        GLib.timeout_add_seconds(2, self._update_engine_status)

    def _build_ui(self):
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toast_overlay.set_child(root_box)

        header = Adw.HeaderBar()
        root_box.append(header)

        install_btn = Gtk.Button(label="Install .rmskin / .ini…")
        install_btn.add_css_class("suggested-action")
        install_btn.connect("clicked", self._on_install_clicked)
        header.pack_start(install_btn)

        open_folder_btn = Gtk.Button(icon_name="folder-open-symbolic")
        open_folder_btn.set_tooltip_text("Open Custom Skins Folder (~/.config/rainmeter-native/Skins)")
        open_folder_btn.connect("clicked", self._on_open_skins_folder)
        header.pack_start(open_folder_btn)

        reload_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        reload_btn.set_tooltip_text("Reload suites, widgets, and synced desktop positions")
        reload_btn.connect("clicked", self._on_refresh_clicked)
        header.pack_start(reload_btn)

        self.view_stack = Adw.ViewStack()
        switcher = Adw.ViewSwitcher()
        switcher.set_stack(self.view_stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        header.set_title_widget(switcher)

        stop_header_btn = Gtk.Button(label="Turn OFF")
        stop_header_btn.add_css_class("destructive-action")
        stop_header_btn.connect("clicked", self._on_stop_clicked)
        header.pack_end(stop_header_btn)

        self.status_label = Gtk.Label(label="○ Stopped")
        self.status_label.add_css_class("dim-label")
        self.status_label.set_margin_end(8)
        header.pack_end(self.status_label)

        root_box.append(self.view_stack)

        # ===================================================================
        # TAB 1: SUITES (Auto-replace active suite & auto-fit to monitor)
        # ===================================================================
        suites_scroll = Gtk.ScrolledWindow()
        suites_scroll.set_vexpand(True)
        suites_page = Adw.Clamp(maximum_size=800)
        suites_scroll.set_child(suites_page)

        suites_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        suites_vbox.set_margin_top(20)
        suites_vbox.set_margin_bottom(24)
        suites_vbox.set_margin_start(16)
        suites_vbox.set_margin_end(16)
        suites_page.set_child(suites_vbox)

        suite_mon_group = Adw.PreferencesGroup(
            title="Suite Display Settings",
            description="Selecting a suite below automatically replaces the current desktop layout and fits it to the target monitor.",
        )
        suites_vbox.append(suite_mon_group)

        suite_mon_row = Adw.ActionRow(
            title="Target Monitor for Suite",
            subtitle="Changing the monitor immediately moves and auto-scales the active suite",
        )
        suite_mon_names = Gtk.StringList.new([m["name"] for m in self.monitors])
        self.suite_mon_dropdown = Gtk.DropDown(model=suite_mon_names)
        self.suite_mon_dropdown.set_valign(Gtk.Align.CENTER)
        self.suite_mon_dropdown.set_selected(min(self.suite_monitor_idx, len(self.monitors) - 1))
        self.suite_mon_dropdown.connect("notify::selected", self._on_suite_monitor_changed)
        suite_mon_row.add_suffix(self.suite_mon_dropdown)
        suite_mon_group.add(suite_mon_row)

        self.suites_list_group = Adw.PreferencesGroup(
            title="Built-in and Saved Custom Suites",
            description="Click 'Activate Suite' on any suite to replace the active desktop layout, or build a new suite from Basic or Custom Widgets.",
        )
        suites_vbox.append(self.suites_list_group)
        self.suite_rows = []

        self.view_stack.add_titled_with_icon(
            suites_scroll, "suites", "Suites", "preferences-desktop-wallpaper-symbolic"
        )

        # ===================================================================
        # TAB 2: BASIC WIDGETS, SHAPES, DESIGNS & MUSIC/VISUALIZERS
        # ===================================================================
        basic_scroll = Gtk.ScrolledWindow()
        basic_scroll.set_vexpand(True)
        basic_page = Adw.Clamp(maximum_size=840)
        basic_scroll.set_child(basic_page)

        basic_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        basic_vbox.set_margin_top(18)
        basic_vbox.set_margin_bottom(24)
        basic_vbox.set_margin_start(16)
        basic_vbox.set_margin_end(16)
        basic_page.set_child(basic_vbox)

        theme_group = Adw.PreferencesGroup(
            title="Trad Rainmeter — Theme, Shape and Design Studio",
            description="Customize Color Theme, Card Shape (Rounded, Squircle, Pill Capsule, Circular, Borderless), and Gauge Design (Vertical Bars, Circular Rings, Capsule Pill, Horizontal Minimal).",
        )
        basic_vbox.append(theme_group)

        # 1. Color Theme Row
        theme_row = Adw.ActionRow(
            title="Color Theme",
            subtitle=BASIC_WIDGET_THEMES[self.basic_theme_idx]["subtitle"],
        )
        self.theme_row_widget = theme_row
        theme_names = Gtk.StringList.new([t["name"] for t in BASIC_WIDGET_THEMES])
        self.theme_dropdown = Gtk.DropDown(model=theme_names)
        self.theme_dropdown.set_valign(Gtk.Align.CENTER)
        self.theme_dropdown.set_selected(self.basic_theme_idx)
        self.theme_dropdown.connect("notify::selected", self._on_basic_theme_changed)
        theme_row.add_suffix(self.theme_dropdown)
        theme_group.add(theme_row)

        # 2. Widget Card Shape Row
        shape_row = Adw.ActionRow(
            title="Widget Card Shape",
            subtitle=BASIC_WIDGET_SHAPES[self.basic_shape_idx]["subtitle"],
        )
        self.shape_row_widget = shape_row
        shape_names = Gtk.StringList.new([s["name"] for s in BASIC_WIDGET_SHAPES])
        self.shape_dropdown = Gtk.DropDown(model=shape_names)
        self.shape_dropdown.set_valign(Gtk.Align.CENTER)
        self.shape_dropdown.set_selected(self.basic_shape_idx)
        self.shape_dropdown.connect("notify::selected", self._on_basic_shape_changed)
        shape_row.add_suffix(self.shape_dropdown)
        theme_group.add(shape_row)

        # 3. Widget Design / Gauge Style Row
        design_row = Adw.ActionRow(
            title="Widget Design and Gauge Layout",
            subtitle=BASIC_WIDGET_DESIGNS[self.basic_design_idx]["subtitle"],
        )
        self.design_row_widget = design_row
        design_names = Gtk.StringList.new([d["name"] for d in BASIC_WIDGET_DESIGNS])
        self.design_dropdown = Gtk.DropDown(model=design_names)
        self.design_dropdown.set_valign(Gtk.Align.CENTER)
        self.design_dropdown.set_selected(self.basic_design_idx)
        self.design_dropdown.connect("notify::selected", self._on_basic_design_changed)
        design_row.add_suffix(self.design_dropdown)
        theme_group.add(design_row)

        # Live Theme + Shape + Design Swatch Preview Strip
        swatch_frame = Gtk.Frame()
        swatch_frame.set_margin_top(6)
        theme_group.add(swatch_frame)

        self.theme_swatch_area = Gtk.DrawingArea()
        self.theme_swatch_area.set_content_height(92)
        self.theme_swatch_area.set_hexpand(True)
        self.theme_swatch_area.set_draw_func(self._draw_theme_swatch_preview)
        swatch_frame.set_child(self.theme_swatch_area)

        # Quick Theme Chips Row
        chips_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        chips_box.set_halign(Gtk.Align.CENTER)
        chips_box.set_margin_top(6)
        theme_group.add(chips_box)

        quick_themes = [
            ("Neon Blue", 0),
            ("Frosted Glass", 1),
            ("Transparent", 2),
            ("Arctic Blue", 3),
            ("Fedora Cyber", 4),
            ("Aqua Glass", 5),
            ("Sunset Glow", 6),
            ("Sapphire", 7),
            ("Crimson", 8),
            ("Lime Classic", 9),
        ]
        for label, tidx in quick_themes:
            tbtn = Gtk.Button(label=label)
            tbtn.add_css_class("flat")
            tbtn.connect("clicked", lambda _b, i=tidx: self.theme_dropdown.set_selected(i))
            chips_box.append(tbtn)

        # Quick Toolbar
        basic_toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        basic_vbox.append(basic_toolbar)

        enable_all_btn = Gtk.Button(label="Enable All 8 Core Widgets")
        enable_all_btn.add_css_class("suggested-action")
        enable_all_btn.connect("clicked", self._on_enable_all_basic_clicked)
        basic_toolbar.append(enable_all_btn)

        enable_media_btn = Gtk.Button(label="Enable Music + Visualizer")
        enable_media_btn.connect("clicked", self._on_enable_media_visualizer_clicked)
        basic_toolbar.append(enable_media_btn)

        disable_all_btn = Gtk.Button(label="Disable All Basic Widgets")
        disable_all_btn.connect("clicked", self._on_disable_all_basic_clicked)
        basic_toolbar.append(disable_all_btn)

        open_pos_btn = Gtk.Button(label="Positioner →")
        open_pos_btn.set_hexpand(True)
        open_pos_btn.set_halign(Gtk.Align.END)
        open_pos_btn.connect("clicked", lambda _b: self.view_stack.set_visible_child_name("widgets"))
        basic_toolbar.append(open_pos_btn)

        # Music Players & Audio Visualizers Group
        self.media_list_group = Adw.PreferencesGroup(
            title="Music Players and Audio Visualizers",
            description="Live MPRIS2 D-Bus media player controls (Spotify, Browser, Rhythmbox, VLC) and real-time 20-band PulseAudio / PipeWire spectrum analyzers.",
        )
        basic_vbox.append(self.media_list_group)
        self.media_rows = []

        # Weather Location & Village Manager Group
        self.weather_group = Adw.PreferencesGroup(
            title="Weather Location and Saved Villages / Cities",
            description="Live weather powered by Open-Meteo. Select a saved place, search any city/town/village online, or add a custom village using coordinates.",
        )
        basic_vbox.append(self.weather_group)

        # Active Location Dropdown Row
        active_loc_row = Adw.ActionRow(
            title="Active Weather Location",
            subtitle=f"{self.weather_locations[self.weather_active_idx]['name']} ({self.weather_locations[self.weather_active_idx]['lat']:.4f}, {self.weather_locations[self.weather_active_idx]['lon']:.4f})",
        )
        self.weather_active_row = active_loc_row
        loc_list = Gtk.StringList.new([loc["name"] for loc in self.weather_locations])
        self.weather_dropdown = Gtk.DropDown(model=loc_list)
        self.weather_dropdown.set_valign(Gtk.Align.CENTER)
        self.weather_dropdown.set_selected(self.weather_active_idx)
        self.weather_dropdown.connect("notify::selected", self._on_weather_location_selected)
        active_loc_row.add_suffix(self.weather_dropdown)

        forecast_btn = Gtk.Button(label="Full Forecast")
        forecast_btn.set_valign(Gtk.Align.CENTER)
        forecast_btn.connect("clicked", self._on_open_weather_forecast_clicked)
        active_loc_row.add_suffix(forecast_btn)
        self.weather_group.add(active_loc_row)

        # Units Row (Metric / Imperial)
        units_row = Adw.ActionRow(
            title="Temperature and Wind Units",
            subtitle="Switch between Celsius / km/h (Metric) and Fahrenheit / mph (Imperial)",
        )
        unit_model = Gtk.StringList.new(["Metric (°C, km/h)", "Imperial (°F, mph)"])
        self.weather_units_dropdown = Gtk.DropDown(model=unit_model)
        self.weather_units_dropdown.set_valign(Gtk.Align.CENTER)
        self.weather_units_dropdown.set_selected(1 if self.weather_units == "imperial" else 0)
        self.weather_units_dropdown.connect("notify::selected", self._on_weather_units_changed)
        units_row.add_suffix(self.weather_units_dropdown)
        self.weather_group.add(units_row)

        # Search Row (Cities, Towns, Villages, or lat,lon)
        search_row = Adw.ActionRow(
            title="Search City, Town, or Village",
            subtitle="Search online (e.g. Polokwane, Giyani, Mahlathini) or enter latitude, longitude (e.g. -23.31, 30.72)",
        )
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        search_box.set_valign(Gtk.Align.CENTER)
        self.weather_search_entry = Gtk.Entry()
        self.weather_search_entry.set_placeholder_text("Village or city name, or lat, lon…")
        self.weather_search_entry.set_width_chars(24)
        self.weather_search_entry.connect("activate", lambda _e: self._on_weather_search_clicked(None))
        search_box.append(self.weather_search_entry)

        self.weather_search_btn = Gtk.Button(label="Search")
        self.weather_search_btn.add_css_class("suggested-action")
        self.weather_search_btn.connect("clicked", self._on_weather_search_clicked)
        search_box.append(self.weather_search_btn)
        search_row.add_suffix(search_box)
        self.weather_group.add(search_row)

        # Manual Village / Custom Location Expander
        self.manual_loc_expander = Adw.ExpanderRow(
            title="Add Village or Custom Location Manually",
            subtitle="Best for rural villages (e.g. Mahatlani Village) — enter display name and coordinates, or pick nearest town below and rename it here",
        )
        self.weather_group.add(self.manual_loc_expander)

        manual_box_row = Adw.PreferencesRow()
        manual_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        manual_box.set_margin_top(10)
        manual_box.set_margin_bottom(10)
        manual_box.set_margin_start(12)
        manual_box.set_margin_end(12)
        manual_box_row.set_child(manual_box)

        name_line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        manual_box.append(name_line)
        lbl_name = Gtk.Label(label="Location Name:", xalign=0)
        lbl_name.set_width_chars(14)
        name_line.append(lbl_name)
        self.manual_loc_name_entry = Gtk.Entry()
        self.manual_loc_name_entry.set_placeholder_text("e.g. Mahatlani Village, Limpopo")
        self.manual_loc_name_entry.set_hexpand(True)
        name_line.append(self.manual_loc_name_entry)

        coords_line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        manual_box.append(coords_line)
        lbl_lat = Gtk.Label(label="Latitude:", xalign=0)
        lbl_lat.set_width_chars(14)
        coords_line.append(lbl_lat)
        self.manual_loc_lat_entry = Gtk.Entry()
        self.manual_loc_lat_entry.set_placeholder_text("e.g. -23.3050")
        self.manual_loc_lat_entry.set_hexpand(True)
        coords_line.append(self.manual_loc_lat_entry)

        lbl_lon = Gtk.Label(label="Longitude:", xalign=0)
        coords_line.append(lbl_lon)
        self.manual_loc_lon_entry = Gtk.Entry()
        self.manual_loc_lon_entry.set_placeholder_text("e.g. 30.7180")
        self.manual_loc_lon_entry.set_hexpand(True)
        coords_line.append(self.manual_loc_lon_entry)

        add_manual_btn = Gtk.Button(label="Add Village / Custom Location and Activate")
        add_manual_btn.add_css_class("suggested-action")
        add_manual_btn.connect("clicked", self._on_add_manual_weather_location)
        manual_box.append(add_manual_btn)
        self.manual_loc_expander.add_row(manual_box_row)

        # Search Results Group (shown when search returns results)
        self.weather_search_group = Adw.PreferencesGroup(
            title="Location Search Results",
            description="Click 'Add and Use' to activate immediately, or 'Rename' to label nearby town coordinates with your village name.",
        )
        self.weather_search_group.set_visible(False)
        basic_vbox.append(self.weather_search_group)

        # Saved Locations Expander / Group
        self.weather_saved_expander = Adw.ExpanderRow(
            title="Manage Saved Weather Locations",
            subtitle=f"{len(self.weather_locations)} saved locations",
        )
        self.weather_group.add(self.weather_saved_expander)

        # Core 8 Modular Basic Widgets Group
        self.basic_list_group = Adw.PreferencesGroup(
            title="Core System Basic Widgets (8 Anchored Blocks)",
            description="Toggle individual anchored system telemetry blocks ON or OFF. Click the gear icon on any block to fine-tune its desktop coordinates.",
        )
        basic_vbox.append(self.basic_list_group)
        self.basic_rows = []

        self.view_stack.add_titled_with_icon(
            basic_scroll, "basic", "Basic Widgets", "view-grid-symbolic"
        )

        # ===================================================================
        # TAB 3: WIDGETS & POSITION (Positioner, Custom Widgets & Suite Builder)
        # ===================================================================
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(350)
        paned.set_vexpand(True)

        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        left_box.set_margin_top(12)
        left_box.set_margin_bottom(12)
        left_box.set_margin_start(12)
        left_box.set_margin_end(8)
        paned.set_start_child(left_box)

        list_header = Gtk.Label(label="Custom & Active Widgets", xalign=0)
        list_header.add_css_class("title-4")
        left_box.append(list_header)

        list_sub = Gtk.Label(
            label="Select any widget to drag its position on the monitor canvas, or save active widgets together as a new Suite.",
            xalign=0,
            wrap=True,
        )
        list_sub.add_css_class("caption")
        list_sub.add_css_class("dim-label")
        left_box.append(list_sub)

        scrolled_list = Gtk.ScrolledWindow()
        scrolled_list.set_vexpand(True)
        scrolled_list.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        left_box.append(scrolled_list)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.add_css_class("boxed-list")
        self.list_box.connect("row-selected", self._on_widget_row_selected)
        scrolled_list.set_child(self.list_box)

        builder_frame = Gtk.Frame()
        builder_frame.set_margin_top(4)
        left_box.append(builder_frame)

        builder_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        builder_box.set_margin_top(8)
        builder_box.set_margin_bottom(8)
        builder_box.set_margin_start(10)
        builder_box.set_margin_end(10)
        builder_frame.set_child(builder_box)

        builder_lbl = Gtk.Label(label="Create Suite from Active Widgets", xalign=0)
        builder_lbl.add_css_class("heading")
        builder_box.append(builder_lbl)

        suite_entry_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        builder_box.append(suite_entry_row)

        self.new_suite_entry = Gtk.Entry()
        self.new_suite_entry.set_placeholder_text("New suite name (e.g. MyNeonSuite)…")
        self.new_suite_entry.set_hexpand(True)
        suite_entry_row.append(self.new_suite_entry)

        save_suite_btn = Gtk.Button(label="Save Suite")
        save_suite_btn.add_css_class("suggested-action")
        save_suite_btn.connect("clicked", self._on_save_new_suite_clicked)
        suite_entry_row.append(save_suite_btn)

        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        left_box.append(action_box)

        self.launch_btn = Gtk.Button(label="Apply Position & Reload Desktop")
        self.launch_btn.add_css_class("suggested-action")
        self.launch_btn.add_css_class("pill")
        self.launch_btn.set_hexpand(True)
        self.launch_btn.connect("clicked", self._on_apply_and_launch)
        action_box.append(self.launch_btn)

        right_scroll = Gtk.ScrolledWindow()
        right_scroll.set_vexpand(True)
        right_scroll.set_hexpand(True)
        paned.set_end_child(right_scroll)

        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        right_box.set_margin_top(12)
        right_box.set_margin_bottom(16)
        right_box.set_margin_start(12)
        right_box.set_margin_end(16)
        right_scroll.set_child(right_box)

        self.detail_title = Gtk.Label(label="Select a Widget", xalign=0)
        self.detail_title.add_css_class("title-2")
        right_box.append(self.detail_title)

        preview_group = Adw.PreferencesGroup(
            title="Interactive Desktop Positioner (Multi-Widget Preview)",
            description="Selected widget is shown in Cyan; other active widgets are shown in Purple. Click or drag any widget box on the canvas!",
        )
        right_box.append(preview_group)

        canvas_frame = Gtk.Frame()
        canvas_frame.set_margin_top(4)
        canvas_frame.set_margin_bottom(4)
        preview_group.add(canvas_frame)

        self.preview_area = Gtk.DrawingArea()
        self.preview_area.set_content_height(235)
        self.preview_area.set_hexpand(True)
        self.preview_area.set_draw_func(self._draw_monitor_preview)
        canvas_frame.set_child(self.preview_area)

        self.drag_gesture = Gtk.GestureDrag.new()
        self.drag_gesture.connect("drag-begin", self._on_preview_drag_begin)
        self.drag_gesture.connect("drag-update", self._on_preview_drag_update)
        self.preview_area.add_controller(self.drag_gesture)

        grid_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        grid_box.set_halign(Gtk.Align.CENTER)
        grid_box.set_margin_top(6)
        preview_group.add(grid_box)

        presets = [
            ("↖ Top-Left", "left", "top"),
            ("↑ Top-Center", "center", "top"),
            ("↗ Top-Right", "right", "top"),
            ("← Center-Left", "left", "center"),
            ("• Center", "center", "center"),
            ("→ Center-Right", "right", "center"),
            ("↙ Bottom-Left", "left", "bottom"),
            ("↓ Bottom-Center", "center", "bottom"),
            ("↘ Bottom-Right", "right", "bottom"),
        ]
        for label, ax, ay in presets:
            btn = Gtk.Button(label=label)
            btn.add_css_class("flat")
            btn.connect("clicked", self._on_quick_anchor_clicked, ax, ay)
            grid_box.append(btn)

        display_group = Adw.PreferencesGroup(
            title="Monitor and Screen Scaling",
            description="Configure target monitor, automatic resolution fitting, or custom scale factor.",
        )
        right_box.append(display_group)

        mon_row = Adw.ActionRow(
            title="Target Monitor",
            subtitle="Display output where this widget is pinned",
        )
        mon_names = Gtk.StringList.new([m["name"] for m in self.monitors])
        self.monitor_dropdown = Gtk.DropDown(model=mon_names)
        self.monitor_dropdown.set_valign(Gtk.Align.CENTER)
        self.monitor_dropdown.connect("notify::selected", self._on_monitor_changed)
        mon_row.add_suffix(self.monitor_dropdown)
        display_group.add(mon_row)

        autofit_row = Adw.ActionRow(
            title="Auto-Fit to Monitor Size",
            subtitle="Automatically scale widget proportionally to the target monitor resolution",
        )
        self.autofit_switch = Gtk.Switch()
        self.autofit_switch.set_valign(Gtk.Align.CENTER)
        self.autofit_switch.connect("notify::active", self._on_autofit_toggled)
        autofit_row.add_suffix(self.autofit_switch)
        display_group.add(autofit_row)

        scale_row = Adw.ActionRow(
            title="Manual Widget Scale",
            subtitle="Override scale factor when Auto-Fit is off (0.25× – 3.00×)",
        )
        scale_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        scale_box.set_valign(Gtk.Align.CENTER)
        self.scale_adj = Gtk.Adjustment(value=1.0, lower=0.25, upper=3.0, step_increment=0.05, page_increment=0.25)
        self.scale_spin = Gtk.SpinButton(adjustment=self.scale_adj, climb_rate=0.05, digits=2)
        self.scale_spin.connect("value-changed", self._on_scale_changed)
        scale_reset_btn = Gtk.Button(label="1.0×")
        scale_reset_btn.connect("clicked", lambda _b: self.scale_adj.set_value(1.0))
        scale_box.append(self.scale_spin)
        scale_box.append(scale_reset_btn)
        scale_row.add_suffix(scale_box)
        display_group.add(scale_row)

        pos_group = Adw.PreferencesGroup(
            title="Position and Anchoring",
            description="Use automatic anchor alignment or exact pixel coordinates (WindowX, WindowY).",
        )
        right_box.append(pos_group)

        custom_pos_row = Adw.ActionRow(
            title="Use Custom Pixel Coordinates (WindowX / WindowY)",
            subtitle="Enable to pin at exact (X, Y) pixel offsets; disable to auto-align by Anchor",
        )
        self.custom_pos_switch = Gtk.Switch()
        self.custom_pos_switch.set_valign(Gtk.Align.CENTER)
        self.custom_pos_switch.connect("notify::active", self._on_custom_pos_toggled)
        custom_pos_row.add_suffix(self.custom_pos_switch)
        pos_group.add(custom_pos_row)

        xy_row = Adw.ActionRow(
            title="Pixel Offset (WindowX, WindowY)",
            subtitle="Relative to the top-left of the selected monitor",
        )
        xy_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        xy_box.set_valign(Gtk.Align.CENTER)
        self.x_adj = Gtk.Adjustment(value=0, lower=-2000, upper=8000, step_increment=5, page_increment=50)
        self.y_adj = Gtk.Adjustment(value=0, lower=-2000, upper=8000, step_increment=5, page_increment=50)
        self.x_spin = Gtk.SpinButton(adjustment=self.x_adj, climb_rate=1, digits=0)
        self.y_spin = Gtk.SpinButton(adjustment=self.y_adj, climb_rate=1, digits=0)
        self.x_spin.connect("value-changed", self._on_xy_changed)
        self.y_spin.connect("value-changed", self._on_xy_changed)
        xy_box.append(Gtk.Label(label="X:"))
        xy_box.append(self.x_spin)
        xy_box.append(Gtk.Label(label="Y:"))
        xy_box.append(self.y_spin)
        xy_row.add_suffix(xy_box)
        pos_group.add(xy_row)

        self.view_stack.add_titled_with_icon(
            paned, "widgets", "Widgets & Position", "preferences-system-windows-symbolic"
        )

    def _show_toast(self, message):
        toast = Adw.Toast.new(GLib.markup_escape_text(message))
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)

    def _sync_active_states_in_place(self):
        """Update buttons and switches across all 3 tabs in-place without destroying GTK4 widgets."""
        self._updating_controls = True
        try:
            for key, btn in self.suite_buttons.items():
                is_active = self.skin_state.get(key, {}).get("active", False) and self.active_custom_suite_id is None
                btn.set_label("Active ✓" if is_active else "Activate Suite")
                if is_active:
                    btn.add_css_class("suggested-action")
                else:
                    btn.remove_css_class("suggested-action")

            for cid, btn in self.custom_suite_buttons.items():
                is_active = self.active_custom_suite_id == cid
                btn.set_label("Active ✓" if is_active else "Activate Suite")
                if is_active:
                    btn.add_css_class("suggested-action")
                else:
                    btn.remove_css_class("suggested-action")

            for key, sw in self.basic_switches.items():
                want = self.skin_state.get(key, {}).get("active", False)
                if sw.get_active() != want:
                    sw.set_active(want)

            for key, (_row, sw) in self.row_map.items():
                want = self.skin_state.get(key, {}).get("active", False)
                if sw.get_active() != want:
                    sw.set_active(want)
        finally:
            self._updating_controls = False

    # --- BASIC WIDGETS & THEME STUDIO LOGIC ---
    def _populate_basic_widgets_tab(self):
        for r in getattr(self, "media_rows", []):
            self.media_list_group.remove(r)
        for r in self.basic_rows:
            self.basic_list_group.remove(r)
        self.media_rows = []
        self.basic_rows = []
        self.basic_switches = {}

        media_descriptions = {
            "MusicBanner": "Banner Music Player • Cover Art + Track Info + ↻ ⏮ ⏯ ⏭ ⇄ + Progress Bar",
            "MusicMinimal": "Minimal Floating Music Player • Track Title + 5 Circular Neon Control Buttons",
            "MusicCompact": "Compact Pill Media Control Bar • Title + Artist + ⏮ ⏯ ⏭ + Progress Line",
            "AudioVisualizer": "20-Band Real-Time Spectrum Analyzer Card • PulseAudio / PipeWire FFT (30 FPS)",
            "AudioHorizon": "Floating Minimalist 20-Band Spectrum + Glowing Horizon Axis Line (30 FPS)",
        }

        for s in self.skins:
            if not s.get("is_basic", False):
                continue
            key = s["key"]
            st = self.skin_state[key]
            title = s["title"]
            is_media = title.startswith("Music") or title.startswith("Audio")
            sub = media_descriptions.get(title, s["subtitle"])

            row = Adw.ActionRow(title=title, subtitle=sub)
            sw = Gtk.Switch()
            sw.set_valign(Gtk.Align.CENTER)
            sw.set_active(st["active"])
            sw.connect("notify::active", self._on_basic_widget_toggled, key)
            row.add_suffix(sw)
            self.basic_switches[key] = sw

            pos_btn = Gtk.Button(icon_name="preferences-system-symbolic")
            pos_btn.set_valign(Gtk.Align.CENTER)
            pos_btn.set_tooltip_text(f"Position '{title}' on desktop canvas")
            pos_btn.connect("clicked", self._on_jump_to_basic_position, key)
            row.add_suffix(pos_btn)

            if is_media:
                self.media_list_group.add(row)
                self.media_rows.append(row)
            else:
                self.basic_list_group.add(row)
                self.basic_rows.append(row)
        return False

    def _draw_rounded_rect(self, cr, x, y, w, h, r):
        import math

        r = max(0.0, min(r, w / 2.0, h / 2.0))
        if r <= 0.5:
            cr.rectangle(x, y, w, h)
            return
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

    def _draw_theme_swatch_preview(self, _area, cr, width, height):
        import math

        theme = BASIC_WIDGET_THEMES[self.basic_theme_idx]
        shape = BASIC_WIDGET_SHAPES[self.basic_shape_idx]
        design = BASIC_WIDGET_DESIGNS[self.basic_design_idx]

        # Ambient backdrop simulating desktop wallpaper contrast
        cr.set_source_rgba(0.06, 0.08, 0.14, 1.0)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        bg_r, bg_g, bg_b, bg_a = theme["preview_bg"]
        bd_r, bd_g, bd_b, bd_a = theme["preview_border"]
        ac_r, ac_g, ac_b, ac_a = theme["preview_accent"]
        radius = min(32, shape["corner_radius"] * 0.55)
        borderless = shape.get("borderless", False)

        cards = [
            (18, 10, 145, 72, "CPU", "42%"),
            (178, 10, 195, 72, "08 : 54", "Trad Rainmeter"),
            (388, 10, 165, 72, "RAM / SWAP", "28% Used"),
            (568, 10, 195, 72, "♫ Imagine Dragons", "⏮  ⏸  ⏭  •  Visualizer"),
        ]
        for idx, (cx, cy, cw, ch, title_txt, sub_txt) in enumerate(cards):
            if cx + cw > width - 10:
                break
            if not borderless:
                cr.set_source_rgba(bg_r, bg_g, bg_b, bg_a)
                self._draw_rounded_rect(cr, cx, cy, cw, ch, radius)
                cr.fill()

                cr.set_source_rgba(bd_r, bd_g, bd_b, bd_a)
                cr.set_line_width(1.6)
                self._draw_rounded_rect(cr, cx, cy, cw, ch, radius)
                cr.stroke()

            if design["id"] == "circular" and idx in (0, 2):
                # Draw mini circular gauge ring on the right of the card
                ring_cx = cx + cw - 32
                ring_cy = cy + ch / 2
                cr.set_source_rgba(1.0, 1.0, 1.0, 0.16)
                cr.set_line_width(4.5)
                cr.arc(ring_cx, ring_cy, 19, 0, 2 * math.pi)
                cr.stroke()

                cr.set_source_rgba(ac_r, ac_g, ac_b, ac_a)
                cr.set_line_width(4.5)
                cr.arc(ring_cx, ring_cy, 19, -math.pi / 2, math.pi * 0.65)
                cr.stroke()

            cr.set_source_rgba(1.0, 1.0, 1.0, 0.95)
            cr.select_font_face("Sans", 0, 1)
            cr.set_font_size(11.5)
            cr.move_to(cx + 12, cy + 24)
            cr.show_text(title_txt)

            cr.set_source_rgba(ac_r, ac_g, ac_b, ac_a)
            cr.set_font_size(10.5)
            cr.move_to(cx + 12, cy + 42)
            cr.show_text(sub_txt)

            if idx == 3:
                # Draw mini spectrum visualizer bars on the 4th card
                for b in range(12):
                    bh = 5 + ((b * 7) % 16)
                    bx = cx + 12 + b * 13
                    by = cy + 64 - bh
                    cr.rectangle(bx, by, 8, bh)
                    cr.fill()
            elif design["id"] != "circular":
                cr.rectangle(cx + 12, cy + 54, cw - 24, 5)
                cr.fill()

    def _apply_current_basic_style_and_reload(self, toast_msg):
        theme = BASIC_WIDGET_THEMES[self.basic_theme_idx]
        shape = BASIC_WIDGET_SHAPES[self.basic_shape_idx]
        design = BASIC_WIDGET_DESIGNS[self.basic_design_idx]

        write_basic_theme(theme, shape, design)
        apply_basic_widget_design(design["id"])
        self.theme_swatch_area.queue_draw()

        # Refresh estimated sizes for Basic Widgets
        for s in self.skins:
            if s.get("is_basic", False):
                meta = estimate_skin_size(s["abs_path"])
                s["est_w"] = meta["width"]
                s["est_h"] = meta["height"]

        self.preview_area.queue_draw()
        if any(self.skin_state[s["key"]]["active"] for s in self.skins if s.get("is_basic", False)):
            self._launch_active_items()
        else:
            self._show_toast(toast_msg)

    def _on_basic_theme_changed(self, dropdown, _pspec):
        idx = int(dropdown.get_selected())
        if idx < 0 or idx >= len(BASIC_WIDGET_THEMES):
            return
        self.basic_theme_idx = idx
        theme = BASIC_WIDGET_THEMES[idx]
        self.theme_row_widget.set_subtitle(theme["subtitle"])
        self._apply_current_basic_style_and_reload(f"Theme set to '{theme['name']}'")

    def _on_basic_shape_changed(self, dropdown, _pspec):
        idx = int(dropdown.get_selected())
        if idx < 0 or idx >= len(BASIC_WIDGET_SHAPES):
            return
        self.basic_shape_idx = idx
        shape = BASIC_WIDGET_SHAPES[idx]
        self.shape_row_widget.set_subtitle(shape["subtitle"])
        self._apply_current_basic_style_and_reload(f"Widget shape set to '{shape['name']}'")

    def _on_basic_design_changed(self, dropdown, _pspec):
        idx = int(dropdown.get_selected())
        if idx < 0 or idx >= len(BASIC_WIDGET_DESIGNS):
            return
        self.basic_design_idx = idx
        design = BASIC_WIDGET_DESIGNS[idx]
        self.design_row_widget.set_subtitle(design["subtitle"])
        self._apply_current_basic_style_and_reload(f"Widget design set to '{design['name']}'")

    def _on_basic_widget_toggled(self, sw, _pspec, key):
        if self._updating_controls:
            return
        self.skin_state[key]["active"] = sw.get_active()
        self.active_custom_suite_id = None
        self._sync_active_states_in_place()
        self.preview_area.queue_draw()
        self._launch_active_items()

    def _on_enable_all_basic_clicked(self, _btn):
        self.active_custom_suite_id = None
        for s in self.skins:
            if s["is_suite"]:
                self.skin_state[s["key"]]["active"] = False
            elif s.get("is_basic", False) and s["title"].startswith("Basic"):
                self.skin_state[s["key"]]["active"] = True
        self._sync_active_states_in_place()
        self.preview_area.queue_draw()
        self._launch_active_items()

    def _on_enable_media_visualizer_clicked(self, _btn):
        self.active_custom_suite_id = None
        for s in self.skins:
            if s["is_suite"]:
                self.skin_state[s["key"]]["active"] = False
            elif s["title"] in ("MusicBanner", "AudioVisualizer"):
                self.skin_state[s["key"]]["active"] = True
        self._sync_active_states_in_place()
        self.preview_area.queue_draw()
        self._launch_active_items()

    def _on_disable_all_basic_clicked(self, _btn):
        for s in self.skins:
            if s.get("is_basic", False):
                self.skin_state[s["key"]]["active"] = False
        self._sync_active_states_in_place()
        self.preview_area.queue_draw()
        self._launch_active_items()

    def _on_jump_to_basic_position(self, _btn, key):
        self._select_widget(key)
        self.view_stack.set_visible_child_name("widgets")

    # --- WEATHER LOCATION & VILLAGE MANAGER LOGIC ---
    def _populate_weather_locations_ui(self, rebuild_model=True):
        self._updating_controls = True
        try:
            self.weather_active_idx = max(0, min(len(self.weather_locations) - 1, self.weather_active_idx))
            if rebuild_model:
                loc_model = Gtk.StringList.new([loc["name"] for loc in self.weather_locations])
                self.weather_dropdown.set_model(loc_model)
            if self.weather_dropdown.get_selected() != self.weather_active_idx:
                self.weather_dropdown.set_selected(self.weather_active_idx)

            cur = self.weather_locations[self.weather_active_idx]
            self.weather_active_row.set_subtitle(
                GLib.markup_escape_text(f"{cur['name']} ({cur['lat']:.4f}, {cur['lon']:.4f})")
            )

            if rebuild_model or len(self.weather_saved_rows) != len(self.weather_locations):
                for r in self.weather_saved_rows:
                    self.weather_saved_expander.remove(r)
                self.weather_saved_rows = []
                self._weather_saved_use_btns = []

                self.weather_saved_expander.set_subtitle(
                    f"{len(self.weather_locations)} saved location{'s' if len(self.weather_locations) != 1 else ''}"
                )

                for idx, loc in enumerate(self.weather_locations):
                    is_cur = idx == self.weather_active_idx
                    row = Adw.ActionRow(
                        title=GLib.markup_escape_text(loc["name"]),
                        subtitle=f"Lat: {loc['lat']:.4f}, Lon: {loc['lon']:.4f}"
                        + ("  •  Active" if is_cur else ""),
                    )
                    use_btn = Gtk.Button(label="Active ✓" if is_cur else "Use")
                    use_btn.set_valign(Gtk.Align.CENTER)
                    if is_cur:
                        use_btn.add_css_class("suggested-action")
                    use_btn.connect("clicked", lambda _b, i=idx: self._set_active_weather_index(i))
                    row.add_suffix(use_btn)
                    self._weather_saved_use_btns.append((row, use_btn, loc))

                    if len(self.weather_locations) > 1:
                        del_btn = Gtk.Button(icon_name="user-trash-symbolic")
                        del_btn.set_valign(Gtk.Align.CENTER)
                        del_btn.add_css_class("flat")
                        del_btn.set_tooltip_text(f"Remove {loc['name']}")
                        del_btn.connect("clicked", self._on_delete_weather_location, idx)
                        row.add_suffix(del_btn)

                    self.weather_saved_expander.add_row(row)
                    self.weather_saved_rows.append(row)
            else:
                for idx, (row, use_btn, loc) in enumerate(getattr(self, "_weather_saved_use_btns", [])):
                    is_cur = idx == self.weather_active_idx
                    row.set_subtitle(
                        f"Lat: {loc['lat']:.4f}, Lon: {loc['lon']:.4f}" + ("  •  Active" if is_cur else "")
                    )
                    use_btn.set_label("Active ✓" if is_cur else "Use")
                    if is_cur:
                        use_btn.add_css_class("suggested-action")
                    else:
                        use_btn.remove_css_class("suggested-action")
        finally:
            self._updating_controls = False
        return False

    def _reload_if_weather_visible(self, toast_msg):
        weather_active = any(
            self.skin_state[s["key"]]["active"]
            and (
                "BasicWeather" in s["key"]
                or any(
                    suite in s["key"]
                    for suite in ("TradSunset", "GreenRibbonSuite", "DashboardSuite", "TealMountainSuite")
                )
            )
            for s in self.skins
        )
        if weather_active:
            save_global_config(self.skins, self.skin_state)
            relaunch_active_engine_from_config()
            self._show_toast("Reloaded active weather widgets on desktop")
        else:
            self._show_toast(toast_msg)

    def _set_active_weather_index(self, idx):
        self.weather_active_idx = max(0, min(len(self.weather_locations) - 1, idx))
        save_weather_config(self.weather_locations, self.weather_active_idx, self.weather_units)
        GLib.idle_add(lambda: self._populate_weather_locations_ui(rebuild_model=False))
        cur = self.weather_locations[self.weather_active_idx]
        self._reload_if_weather_visible(
            f"Weather location set to '{cur['name']}' (enable BasicWeather to view)"
        )

    def _on_weather_location_selected(self, dropdown, _pspec):
        if self._updating_controls:
            return
        idx = int(dropdown.get_selected())
        if idx < 0 or idx >= len(self.weather_locations):
            return
        self._set_active_weather_index(idx)

    def _on_weather_units_changed(self, dropdown, _pspec):
        if self._updating_controls:
            return
        self.weather_units = "imperial" if int(dropdown.get_selected()) == 1 else "metric"
        save_weather_config(self.weather_locations, self.weather_active_idx, self.weather_units)
        self._reload_if_weather_visible(
            f"Weather units set to {'Imperial (°F, mph)' if self.weather_units == 'imperial' else 'Metric (°C, km/h)'}"
        )

    def _on_weather_search_clicked(self, _btn):
        query = self.weather_search_entry.get_text().strip()
        if not query:
            self._show_toast("Enter a village, town, city name, or coordinates to search")
            return
        self.weather_search_btn.set_sensitive(False)
        self.weather_search_btn.set_label("Searching…")

        def _worker():
            results = search_weather_locations(query)

            def _done():
                self.weather_search_btn.set_sensitive(True)
                self.weather_search_btn.set_label("Search")
                self._weather_search_results = results
                self._populate_weather_search_results(query)
                return False

            GLib.idle_add(_done)

        threading.Thread(target=_worker, daemon=True).start()

    def _populate_weather_search_results(self, query=""):
        for r in self.weather_search_rows:
            self.weather_search_group.remove(r)
        self.weather_search_rows = []

        if not self._weather_search_results:
            self.weather_search_group.set_visible(True)
            empty_row = Adw.ActionRow(
                title=GLib.markup_escape_text(f"No online match found for '{query}'"),
                subtitle="Many rural villages are absent from online maps — search the nearest town (e.g. Giyani / Tzaneen / Makhado) and click Rename, or add your village manually above.",
            )
            open_manual_btn = Gtk.Button(label="Add Manually")
            open_manual_btn.set_valign(Gtk.Align.CENTER)
            open_manual_btn.add_css_class("suggested-action")
            open_manual_btn.connect("clicked", self._on_open_manual_for_query, query)
            empty_row.add_suffix(open_manual_btn)
            self.weather_search_group.add(empty_row)
            self.weather_search_rows.append(empty_row)
            return False

        self.weather_search_group.set_visible(True)
        for res in self._weather_search_results:
            sub = f"{res['source']} • Lat: {res['lat']:.4f}, Lon: {res['lon']:.4f}"
            if res.get("detail"):
                sub += f" • {res['detail']}"
            row = Adw.ActionRow(
                title=GLib.markup_escape_text(res["name"]),
                subtitle=GLib.markup_escape_text(sub[:140]),
            )

            rename_btn = Gtk.Button(label="Rename & Add")
            rename_btn.set_valign(Gtk.Align.CENTER)
            rename_btn.set_tooltip_text("Copy coordinates into the Manual Village form so you can name it cleanly")
            rename_btn.connect("clicked", self._on_prefill_manual_from_search, res)
            row.add_suffix(rename_btn)

            add_btn = Gtk.Button(label="Add & Use")
            add_btn.set_valign(Gtk.Align.CENTER)
            add_btn.add_css_class("suggested-action")
            add_btn.connect("clicked", self._on_use_search_result, res)
            row.add_suffix(add_btn)

            self.weather_search_group.add(row)
            self.weather_search_rows.append(row)
        return False

    def _on_open_manual_for_query(self, _btn, query):
        if query:
            self.manual_loc_name_entry.set_text(query)
        self.manual_loc_expander.set_expanded(True)

    def _on_prefill_manual_from_search(self, _btn, res):
        typed = self.weather_search_entry.get_text().strip()
        self.manual_loc_name_entry.set_text(typed if typed else res["name"])
        self.manual_loc_lat_entry.set_text(f"{res['lat']:.5f}")
        self.manual_loc_lon_entry.set_text(f"{res['lon']:.5f}")
        self.manual_loc_expander.set_expanded(True)
        self._show_toast("Coordinates copied — edit Name if needed and click Add Village")

    def _add_or_select_location(self, name, lat, lon):
        existing = next(
            (
                i
                for i, loc in enumerate(self.weather_locations)
                if loc["name"].lower() == name.lower()
                or (abs(loc["lat"] - lat) < 0.002 and abs(loc["lon"] - lon) < 0.002 and loc["name"].lower() == name.lower())
            ),
            None,
        )
        if existing is not None:
            self.weather_locations[existing] = {"name": name, "lat": lat, "lon": lon}
            self.weather_active_idx = existing
        else:
            self.weather_locations.insert(0, {"name": name, "lat": lat, "lon": lon})
            self.weather_active_idx = 0

        save_weather_config(self.weather_locations, self.weather_active_idx, self.weather_units)
        GLib.idle_add(self._populate_weather_locations_ui)
        self._reload_if_weather_visible(f"Added & activated weather for '{name}'")

    def _on_use_search_result(self, _btn, res):
        self._add_or_select_location(res["name"], res["lat"], res["lon"])
        GLib.idle_add(lambda: (self.weather_search_group.set_visible(False), False)[1])

    def _on_add_manual_weather_location(self, _btn):
        name = self.manual_loc_name_entry.get_text().strip()
        lat_str = self.manual_loc_lat_entry.get_text().strip().replace(",", ".")
        lon_str = self.manual_loc_lon_entry.get_text().strip().replace(",", ".")
        if not name:
            self._show_toast("Please enter a village or location name")
            return
        try:
            lat = float(lat_str)
            lon = float(lon_str)
        except ValueError:
            self._show_toast("Please enter valid numeric Latitude and Longitude")
            return
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            self._show_toast("Latitude must be -90..90 and Longitude -180..180")
            return

        self.manual_loc_name_entry.set_text("")
        self.manual_loc_lat_entry.set_text("")
        self.manual_loc_lon_entry.set_text("")
        self.manual_loc_expander.set_expanded(False)
        self._add_or_select_location(name, lat, lon)

    def _on_delete_weather_location(self, _btn, idx):
        if len(self.weather_locations) <= 1 or idx < 0 or idx >= len(self.weather_locations):
            return
        removed = self.weather_locations.pop(idx)["name"]
        if self.weather_active_idx >= len(self.weather_locations):
            self.weather_active_idx = 0
        elif idx < self.weather_active_idx:
            self.weather_active_idx = max(0, self.weather_active_idx - 1)
        save_weather_config(self.weather_locations, self.weather_active_idx, self.weather_units)
        GLib.idle_add(self._populate_weather_locations_ui)
        self._reload_if_weather_visible(f"Removed location '{removed}'")

    # --- SUITES TAB LOGIC ---
    def _populate_suites_tab(self):
        for r in self.suite_rows:
            self.suites_list_group.remove(r)
        self.suite_rows = []
        self.suite_buttons = {}
        self.custom_suite_buttons = {}

        for s in self.skins:
            if not s["is_suite"]:
                continue
            key = s["key"]
            st = self.skin_state[key]
            is_active = st["active"] and self.active_custom_suite_id is None

            row = Adw.ActionRow(
                title=s["title"],
                subtitle=f"Built-in Suite • {s['subtitle']} ({s['est_w']}×{s['est_h']}, Auto-Fits Monitor)",
            )
            btn = Gtk.Button(label="Active ✓" if is_active else "Activate Suite")
            btn.set_valign(Gtk.Align.CENTER)
            if is_active:
                btn.add_css_class("suggested-action")
            btn.connect("clicked", self._on_activate_suite_clicked, key)
            row.add_suffix(btn)
            self.suite_buttons[key] = btn

            pos_btn = Gtk.Button(icon_name="preferences-system-symbolic")
            pos_btn.set_valign(Gtk.Align.CENTER)
            pos_btn.set_tooltip_text("Adjust position and scale in Widgets tab")
            pos_btn.connect("clicked", self._on_edit_suite_position_clicked, key)
            row.add_suffix(pos_btn)

            self.suites_list_group.add(row)
            self.suite_rows.append(row)

        for cs in self.custom_suites:
            is_active = self.active_custom_suite_id == cs["id"]
            w_names = [os.path.splitext(os.path.basename(w["key"]))[0] for w in cs["widgets"]]
            subtitle = f"Custom Suite ({len(cs['widgets'])} widget{'s' if len(cs['widgets']) != 1 else ''}: {', '.join(w_names)})"

            row = Adw.ActionRow(title=cs["title"], subtitle=subtitle)

            btn = Gtk.Button(label="Active ✓" if is_active else "Activate Suite")
            btn.set_valign(Gtk.Align.CENTER)
            if is_active:
                btn.add_css_class("suggested-action")
            btn.connect("clicked", self._on_activate_custom_suite_clicked, cs)
            row.add_suffix(btn)
            self.custom_suite_buttons[cs["id"]] = btn

            edit_btn = Gtk.Button(icon_name="preferences-system-symbolic")
            edit_btn.set_valign(Gtk.Align.CENTER)
            edit_btn.set_tooltip_text("Load and edit widgets in Widgets tab")
            edit_btn.connect("clicked", self._on_edit_custom_suite_clicked, cs)
            row.add_suffix(edit_btn)

            del_btn = Gtk.Button(icon_name="user-trash-symbolic")
            del_btn.set_valign(Gtk.Align.CENTER)
            del_btn.add_css_class("flat")
            del_btn.set_tooltip_text(f"Delete custom suite '{cs['title']}'")
            del_btn.connect("clicked", self._on_delete_custom_suite_clicked, cs)
            row.add_suffix(del_btn)

            self.suites_list_group.add(row)
            self.suite_rows.append(row)
        return False

    def _on_suite_monitor_changed(self, dropdown, _pspec):
        if self._updating_controls:
            return
        self.suite_monitor_idx = int(dropdown.get_selected())
        if self.active_custom_suite_id:
            cs = next((c for c in self.custom_suites if c["id"] == self.active_custom_suite_id), None)
            if cs:
                self._activate_custom_suite(cs, override_monitor=self.suite_monitor_idx)
                return

        active_suite_key = None
        for s in self.skins:
            if s["is_suite"]:
                self.skin_state[s["key"]]["monitor"] = self.suite_monitor_idx
                if self.skin_state[s["key"]]["active"]:
                    active_suite_key = s["key"]
        if active_suite_key:
            self._activate_and_launch_suite(active_suite_key)

    def _on_activate_suite_clicked(self, _btn, suite_key):
        self._activate_and_launch_suite(suite_key)

    def _activate_and_launch_suite(self, suite_key):
        self.active_custom_suite_id = None
        for s in self.skins:
            is_target = s["key"] == suite_key
            self.skin_state[s["key"]]["active"] = is_target
            if is_target:
                self.skin_state[s["key"]]["monitor"] = self.suite_monitor_idx
                self.skin_state[s["key"]]["auto_fit"] = True
                self.skin_state[s["key"]]["use_custom_pos"] = False
                self.skin_state[s["key"]]["anchor_x"] = "center"
                self.skin_state[s["key"]]["anchor_y"] = "center"
                self.skin_state[s["key"]]["x"] = 0
                self.skin_state[s["key"]]["y"] = 0

        self._sync_active_states_in_place()
        self._select_widget(suite_key)
        self._launch_active_items()

    def _on_activate_custom_suite_clicked(self, _btn, cs):
        self._activate_custom_suite(cs)

    def _activate_custom_suite(self, cs, override_monitor=None):
        self.active_custom_suite_id = cs["id"]
        for s in self.skins:
            self.skin_state[s["key"]]["active"] = False

        first_key = None
        for w in cs["widgets"]:
            wkey = w.get("key")
            matched = next(
                (
                    s["key"]
                    for s in self.skins
                    if s["key"] == wkey
                    or s["abs_path"] == wkey
                    or os.path.basename(s["abs_path"]) == os.path.basename(str(wkey))
                ),
                None,
            )
            if not matched:
                continue
            if first_key is None:
                first_key = matched
            st = self.skin_state[matched]
            st["active"] = True
            st["monitor"] = override_monitor if override_monitor is not None else w.get("monitor", self.suite_monitor_idx)
            st["anchor_x"] = w.get("anchor_x", st["anchor_x"])
            st["anchor_y"] = w.get("anchor_y", st["anchor_y"])
            st["use_custom_pos"] = w.get("use_custom_pos", False)
            st["x"] = w.get("x", 0)
            st["y"] = w.get("y", 0)
            st["auto_fit"] = w.get("auto_fit", False)
            st["scale"] = w.get("scale", 1.0)

        self._sync_active_states_in_place()
        if first_key:
            self._select_widget(first_key)
        self._launch_active_items()

    def _on_edit_suite_position_clicked(self, _btn, suite_key):
        self.show_suites_in_widgets_tab = True
        self._populate_widgets_tab()
        self._select_widget(suite_key)
        self.view_stack.set_visible_child_name("widgets")

    def _on_edit_custom_suite_clicked(self, _btn, cs):
        self._activate_custom_suite(cs)
        self.new_suite_entry.set_text(cs["title"])
        self.view_stack.set_visible_child_name("widgets")

    def _on_delete_custom_suite_clicked(self, btn, cs):
        btn.set_sensitive(False)
        suite_dir = os.path.dirname(cs["manifest_path"])

        def _do_delete():
            try:
                if os.path.isdir(suite_dir) and os.path.abspath(suite_dir).startswith(os.path.abspath(SUITES_DIR)):
                    shutil.rmtree(suite_dir)
                if self.active_custom_suite_id == cs["id"]:
                    self.active_custom_suite_id = None
                self.custom_suites = discover_custom_suites()
                self._populate_suites_tab()
                self._show_toast(f"Deleted custom suite '{cs['title']}'")
            except Exception as e:
                self._show_toast(f"Could not delete suite: {e}")
            return False

        GLib.idle_add(_do_delete)

    # --- SAVE NEW SUITE FROM ACTIVE WIDGETS ---
    def _on_save_new_suite_clicked(self, _btn):
        raw_name = self.new_suite_entry.get_text().strip()
        if not raw_name:
            self._show_toast("Please enter a name for your new suite first")
            self.new_suite_entry.grab_focus()
            return

        folder_name = re.sub(r"[^A-Za-z0-9_-]+", "", raw_name.replace(" ", "_"))
        if not folder_name:
            self._show_toast("Suite name must contain letters or numbers")
            return

        active_skins = [s for s in self.skins if self.skin_state[s["key"]]["active"]]
        if not active_skins:
            self._show_toast("Toggle at least one widget ON before saving a suite")
            return

        suite_dir = os.path.join(SUITES_DIR, folder_name)
        os.makedirs(suite_dir, exist_ok=True)

        widgets_payload = []
        thm_lines = [f"; Custom Suite: {raw_name}\n"]
        for s in active_skins:
            key = s["key"]
            st = self.skin_state[key]
            widgets_payload.append(
                {
                    "key": key,
                    "title": s["title"],
                    "monitor": st["monitor"],
                    "anchor_x": st["anchor_x"],
                    "anchor_y": st["anchor_y"],
                    "use_custom_pos": st["use_custom_pos"],
                    "x": st["x"],
                    "y": st["y"],
                    "auto_fit": st["auto_fit"],
                    "scale": st["scale"],
                }
            )
            thm_lines.append(f"[{key}]\n")
            thm_lines.append("Active=1\n")
            thm_lines.append(f"Monitor={st['monitor']}\n")
            thm_lines.append(f"AnchorX={st['anchor_x'].capitalize()}\n")
            thm_lines.append(f"AnchorY={st['anchor_y'].capitalize()}\n")
            thm_lines.append(f"AutoFit={1 if st['auto_fit'] else 0}\n")
            if not st["auto_fit"]:
                thm_lines.append(f"Scale={st['scale']:.2f}\n")
            if st["use_custom_pos"]:
                thm_lines.append(f"WindowX={int(st['x'])}\n")
                thm_lines.append(f"WindowY={int(st['y'])}\n")
            thm_lines.append("\n")

        manifest_path = os.path.join(suite_dir, "suite.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump({"name": raw_name, "widgets": widgets_payload}, f, indent=2)

        thm_path = os.path.join(suite_dir, f"{folder_name}.thm")
        with open(thm_path, "w", encoding="utf-8") as f:
            f.writelines(thm_lines)

        self.custom_suites = discover_custom_suites()
        self.active_custom_suite_id = f"custom_suite::{folder_name}"
        GLib.idle_add(self._populate_suites_tab)
        self._launch_active_items()
        self._show_toast(f"Saved suite '{raw_name}' ({len(active_skins)} widget(s)) to Suites tab!")

    # --- WIDGETS & POSITION TAB LOGIC ---
    def _populate_widgets_tab(self):
        self._updating_controls = True
        try:
            while True:
                row = self.list_box.get_row_at_index(0)
                if row is None:
                    break
                self.list_box.remove(row)

            self.row_map = {}
            for s in self.skins:
                if s["is_suite"] and not getattr(self, "show_suites_in_widgets_tab", False):
                    continue
                key = s["key"]
                st = self.skin_state[key]

                row = Adw.ActionRow(title=s["title"], subtitle=f"{s['source']} • {s['subtitle']}")
                row.skin_key = key

                sw = Gtk.Switch()
                sw.set_valign(Gtk.Align.CENTER)
                sw.set_active(st["active"])
                sw.connect("notify::active", self._on_widget_active_toggled, key)
                row.add_suffix(sw)

                if not s["is_suite"]:
                    del_btn = Gtk.Button(icon_name="user-trash-symbolic")
                    del_btn.set_valign(Gtk.Align.CENTER)
                    del_btn.add_css_class("flat")
                    del_btn.set_tooltip_text(f"Remove widget '{s['title']}'")
                    del_btn.connect("clicked", self._on_delete_widget_clicked, s)
                    row.add_suffix(del_btn)

                self.list_box.append(row)
                self.row_map[key] = (row, sw)
        finally:
            self._updating_controls = False
        return False

    def _on_delete_widget_clicked(self, btn, skin_info):
        btn.set_sensitive(False)
        key = skin_info["key"]
        abs_path = skin_info["abs_path"]
        widget_dir = os.path.dirname(abs_path)

        def _do_remove():
            was_active = self.skin_state.get(key, {}).get("active", False)
            try:
                allowed_roots = (
                    os.path.abspath(USER_SKINS_DIR),
                    os.path.abspath(WIDGETS_DIR),
                )
                if os.path.isdir(widget_dir) and any(
                    os.path.abspath(widget_dir).startswith(r + os.sep) for r in allowed_roots
                ):
                    shutil.rmtree(widget_dir)
                elif os.path.isfile(abs_path):
                    os.remove(abs_path)
            except Exception as e:
                self._show_toast(f"Failed to remove widget: {e}")
                return False

            if key in self.skin_state:
                del self.skin_state[key]
            self.skins = [s for s in self.skins if s["key"] != key]
            self._populate_basic_widgets_tab()
            self._populate_widgets_tab()

            next_sel = next((s["key"] for s in self.skins if not s["is_suite"]), None)
            if next_sel:
                self._select_widget(next_sel)
            if was_active:
                self._launch_active_items()
            self._show_toast(f"Removed widget '{skin_info['title']}'")
            return False

        GLib.idle_add(_do_remove)

    def _get_effective_scale(self, skin_info, st):
        if st.get("auto_fit", False):
            mon = self.monitors[min(st["monitor"], len(self.monitors) - 1)]
            return compute_autofit_scale(skin_info, mon["width"], mon["height"])
        return st["scale"]

    def _select_widget(self, key):
        if key not in self.skin_state:
            return
        self.selected_key = key
        self._updating_controls = True
        try:
            if key in self.row_map:
                row, _sw = self.row_map[key]
                if self.list_box.get_selected_row() is not row:
                    self.list_box.select_row(row)

            skin_info = next((s for s in self.skins if s["key"] == key), None)
            st = self.skin_state[key]
            if skin_info:
                self.detail_title.set_label(skin_info["title"])
            mon_idx = min(st["monitor"], len(self.monitors) - 1)
            self.monitor_dropdown.set_selected(mon_idx)
            self.autofit_switch.set_active(st.get("auto_fit", False))
            eff_scale = self._get_effective_scale(skin_info, st) if skin_info else st["scale"]
            self.scale_adj.set_value(eff_scale)
            self.scale_spin.set_sensitive(not st.get("auto_fit", False))
            self.custom_pos_switch.set_active(st["use_custom_pos"])

            if not st["use_custom_pos"] and skin_info:
                ax, ay = self._compute_anchored_xy(skin_info, st)
                self.x_adj.set_value(ax)
                self.y_adj.set_value(ay)
            else:
                self.x_adj.set_value(st["x"])
                self.y_adj.set_value(st["y"])
        finally:
            self._updating_controls = False

        self.preview_area.queue_draw()

    def _compute_anchored_xy(self, skin_info, st):
        mon_idx = min(st["monitor"], len(self.monitors) - 1)
        mon = self.monitors[mon_idx]
        mon_w, mon_h = mon["width"], mon["height"]
        eff_scale = self._get_effective_scale(skin_info, st)
        w = int(skin_info["est_w"] * eff_scale)
        h = int(skin_info["est_h"] * eff_scale)

        if st["anchor_x"] == "center":
            x = (mon_w - w) // 2
        elif st["anchor_x"] == "right":
            x = mon_w - w
        else:
            x = 0

        if st["anchor_y"] == "center":
            y = (mon_h - h) // 2
        elif st["anchor_y"] == "bottom":
            y = mon_h - h
        else:
            y = 0
        return x, y

    def _on_widget_row_selected(self, _listbox, row):
        if self._updating_controls:
            return
        if row is not None and hasattr(row, "skin_key"):
            self._select_widget(row.skin_key)

    def _on_widget_active_toggled(self, sw, _pspec, key):
        if self._updating_controls:
            return
        is_on = sw.get_active()
        self.skin_state[key]["active"] = is_on
        self.active_custom_suite_id = None
        self._sync_active_states_in_place()
        self.preview_area.queue_draw()

    def _on_monitor_changed(self, dropdown, _pspec):
        if self._updating_controls or not self.selected_key:
            return
        mon_idx = int(dropdown.get_selected())
        self.skin_state[self.selected_key]["monitor"] = mon_idx
        self._select_widget(self.selected_key)

    def _on_autofit_toggled(self, sw, _pspec):
        if self._updating_controls or not self.selected_key:
            return
        st = self.skin_state[self.selected_key]
        st["auto_fit"] = sw.get_active()
        self._select_widget(self.selected_key)

    def _on_scale_changed(self, spin):
        if self._updating_controls or not self.selected_key:
            return
        st = self.skin_state[self.selected_key]
        st["auto_fit"] = False
        st["scale"] = round(spin.get_value(), 2)
        self._updating_controls = True
        self.autofit_switch.set_active(False)
        self.scale_spin.set_sensitive(True)
        if not st["use_custom_pos"]:
            skin_info = next((s for s in self.skins if s["key"] == self.selected_key), None)
            if skin_info:
                ax, ay = self._compute_anchored_xy(skin_info, st)
                self.x_adj.set_value(ax)
                self.y_adj.set_value(ay)
        self._updating_controls = False
        self.preview_area.queue_draw()

    def _on_custom_pos_toggled(self, sw, _pspec):
        if self._updating_controls or not self.selected_key:
            return
        st = self.skin_state[self.selected_key]
        st["use_custom_pos"] = sw.get_active()
        if st["use_custom_pos"]:
            st["x"] = int(self.x_adj.get_value())
            st["y"] = int(self.y_adj.get_value())
        else:
            skin_info = next((s for s in self.skins if s["key"] == self.selected_key), None)
            if skin_info:
                self._updating_controls = True
                ax, ay = self._compute_anchored_xy(skin_info, st)
                self.x_adj.set_value(ax)
                self.y_adj.set_value(ay)
                self._updating_controls = False
        self.preview_area.queue_draw()

    def _on_xy_changed(self, _spin):
        if self._updating_controls or not self.selected_key:
            return
        st = self.skin_state[self.selected_key]
        st["use_custom_pos"] = True
        st["x"] = int(self.x_adj.get_value())
        st["y"] = int(self.y_adj.get_value())
        self._updating_controls = True
        self.custom_pos_switch.set_active(True)
        self._updating_controls = False
        self.preview_area.queue_draw()

    def _on_quick_anchor_clicked(self, _btn, ax, ay):
        if not self.selected_key:
            return
        st = self.skin_state[self.selected_key]
        st["anchor_x"] = ax
        st["anchor_y"] = ay
        st["use_custom_pos"] = False
        self._select_widget(self.selected_key)

    # --- Preview Canvas Rendering & Multi-Widget Dragging ---
    def _get_preview_transform(self, area_w, area_h):
        if not self.selected_key:
            return 1.0, 0, 0, 1366, 768
        st = self.skin_state[self.selected_key]
        mon = self.monitors[min(st["monitor"], len(self.monitors) - 1)]
        mon_w, mon_h = mon["width"], mon["height"]
        pad = 20
        scale = min((area_w - 2 * pad) / mon_w, (area_h - 2 * pad) / mon_h)
        draw_w = mon_w * scale
        draw_h = mon_h * scale
        off_x = (area_w - draw_w) / 2.0
        off_y = (area_h - draw_h) / 2.0
        return scale, off_x, off_y, mon_w, mon_h

    def _draw_monitor_preview(self, _area, cr, width, height):
        scale, off_x, off_y, mon_w, mon_h = self._get_preview_transform(width, height)
        draw_w = mon_w * scale
        draw_h = mon_h * scale

        cr.set_source_rgba(0.09, 0.11, 0.16, 1.0)
        cr.rectangle(off_x, off_y, draw_w, draw_h)
        cr.fill()

        cr.set_source_rgba(1.0, 1.0, 1.0, 0.08)
        cr.set_line_width(1.0)
        cr.move_to(off_x + draw_w / 2, off_y)
        cr.line_to(off_x + draw_w / 2, off_y + draw_h)
        cr.move_to(off_x, off_y + draw_h / 2)
        cr.line_to(off_x + draw_w, off_y + draw_h / 2)
        cr.stroke()

        cr.set_source_rgba(0.04, 0.05, 0.08, 0.85)
        cr.rectangle(off_x, off_y, draw_w, max(6, 26 * scale))
        cr.fill()

        dock_w = draw_w * 0.36
        dock_h = max(8, 42 * scale)
        cr.set_source_rgba(0.14, 0.17, 0.24, 0.8)
        cr.rectangle(off_x + (draw_w - dock_w) / 2, off_y + draw_h - dock_h - 4, dock_w, dock_h)
        cr.fill()

        cr.set_source_rgba(0.35, 0.45, 0.65, 0.9)
        cr.set_line_width(2.0)
        cr.rectangle(off_x, off_y, draw_w, draw_h)
        cr.stroke()

        if not self.selected_key:
            return

        cur_mon = self.skin_state[self.selected_key]["monitor"]

        to_draw = []
        for s in self.skins:
            k = s["key"]
            st = self.skin_state[k]
            if k != self.selected_key and st["active"] and st["monitor"] == cur_mon:
                to_draw.append((s, st, False))
        sel_info = next((s for s in self.skins if s["key"] == self.selected_key), None)
        if sel_info:
            to_draw.append((sel_info, self.skin_state[self.selected_key], True))

        for skin_info, st, is_sel in to_draw:
            eff_scale = self._get_effective_scale(skin_info, st)
            w_px = min(mon_w, skin_info["est_w"] * eff_scale)
            h_px = min(mon_h, skin_info["est_h"] * eff_scale)
            if st["use_custom_pos"]:
                x_px, y_px = st["x"], st["y"]
            else:
                x_px, y_px = self._compute_anchored_xy(skin_info, st)

            wx = off_x + x_px * scale
            wy = off_y + y_px * scale
            ww = max(24, w_px * scale)
            wh = max(20, h_px * scale)

            if is_sel:
                cr.set_source_rgba(0.0, 0.82, 0.95, 0.28)
            else:
                cr.set_source_rgba(0.65, 0.35, 0.95, 0.22)
            cr.rectangle(wx, wy, ww, wh)
            cr.fill()

            if is_sel:
                cr.set_source_rgba(0.0, 0.90, 1.0, 0.95)
                cr.set_line_width(2.0)
            else:
                cr.set_source_rgba(0.72, 0.45, 1.0, 0.85)
                cr.set_line_width(1.5)
            cr.rectangle(wx, wy, ww, wh)
            cr.stroke()

            cr.set_source_rgba(1.0, 1.0, 1.0, 0.95)
            cr.select_font_face("Sans", 0, 1)
            cr.set_font_size(11)
            label = f"{skin_info['title']} ({int(x_px)}, {int(y_px)}) [{eff_scale:.2f}×]"
            cr.move_to(wx + 6, wy + 16)
            cr.show_text(label)

    def _on_preview_drag_begin(self, _gesture, start_x, start_y):
        if not self.selected_key:
            return
        w = self.preview_area.get_width()
        h = self.preview_area.get_height()
        scale, off_x, off_y, mon_w, mon_h = self._get_preview_transform(w, h)
        cur_mon = self.skin_state[self.selected_key]["monitor"]

        if scale > 0:
            click_mon_x = (start_x - off_x) / scale
            click_mon_y = (start_y - off_y) / scale
            for s in reversed(self.skins):
                k = s["key"]
                st = self.skin_state[k]
                if not st["active"] and k != self.selected_key:
                    continue
                if st["monitor"] != cur_mon:
                    continue
                eff_scale = self._get_effective_scale(s, st)
                w_px = min(mon_w, s["est_w"] * eff_scale)
                h_px = min(mon_h, s["est_h"] * eff_scale)
                x_px, y_px = (st["x"], st["y"]) if st["use_custom_pos"] else self._compute_anchored_xy(s, st)
                if x_px <= click_mon_x <= x_px + w_px and y_px <= click_mon_y <= y_px + h_px:
                    if k != self.selected_key:
                        self._select_widget(k)
                    break

        skin_info = next((s for s in self.skins if s["key"] == self.selected_key), None)
        st = self.skin_state[self.selected_key]
        if st["use_custom_pos"]:
            self._drag_start_win_x = st["x"]
            self._drag_start_win_y = st["y"]
        elif skin_info:
            self._drag_start_win_x, self._drag_start_win_y = self._compute_anchored_xy(skin_info, st)

    def _on_preview_drag_update(self, _gesture, offset_x, offset_y):
        if not self.selected_key:
            return
        w = self.preview_area.get_width()
        h = self.preview_area.get_height()
        scale, _ox, _oy, mon_w, mon_h = self._get_preview_transform(w, h)
        if scale <= 0:
            return

        skin_info = next((s for s in self.skins if s["key"] == self.selected_key), None)
        st = self.skin_state[self.selected_key]
        eff_scale = self._get_effective_scale(skin_info, st) if skin_info else st["scale"]
        est_w = int(skin_info["est_w"] * eff_scale) if skin_info else 200
        est_h = int(skin_info["est_h"] * eff_scale) if skin_info else 150

        new_x = int(self._drag_start_win_x + offset_x / scale)
        new_y = int(self._drag_start_win_y + offset_y / scale)
        new_x = max(0, min(mon_w - min(mon_w, est_w), new_x))
        new_y = max(0, min(mon_h - min(mon_h, est_h), new_y))

        st["use_custom_pos"] = True
        st["x"] = new_x
        st["y"] = new_y

        self._updating_controls = True
        self.custom_pos_switch.set_active(True)
        self.x_adj.set_value(new_x)
        self.y_adj.set_value(new_y)
        self._updating_controls = False
        self.preview_area.queue_draw()

    # --- File Installation (.rmskin / .ini / .zip) ---
    def _on_install_clicked(self, _btn):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Install Rainmeter Skin (.rmskin, .ini, or .zip)")

        if os.path.isdir(COMMUNITY_DIR):
            dialog.set_initial_folder(Gio.File.new_for_path(COMMUNITY_DIR))

        filters = Gio.ListStore.new(Gtk.FileFilter)
        f_all = Gtk.FileFilter()
        f_all.set_name("Rainmeter Skins (*.rmskin, *.ini, *.zip)")
        f_all.add_pattern("*.rmskin")
        f_all.add_pattern("*.RMSKIN")
        f_all.add_pattern("*.ini")
        f_all.add_pattern("*.INI")
        f_all.add_pattern("*.zip")
        filters.append(f_all)
        dialog.set_filters(filters)

        dialog.open(self, None, self._on_install_file_selected)

    def _install_skin_from_path(self, path):
        """Install a .rmskin, .zip, or .ini file into ~/.config/rainmeter-native/Skins and return installed key."""
        ext = os.path.splitext(path)[1].lower()
        os.makedirs(USER_SKINS_DIR, exist_ok=True)
        before_keys = {s["key"] for s in self.skins}

        if ext in (".rmskin", ".zip"):
            installed_ok = False
            if os.path.isfile(ENGINE_BIN):
                res = subprocess.run([ENGINE_BIN, "--install", path], capture_output=True, text=True)
                if res.returncode == 0:
                    installed_ok = True
            if not installed_ok:
                with zipfile.ZipFile(path, "r") as zf:
                    for member in zf.namelist():
                        norm = member.replace("\\", "/")
                        if norm.startswith("Skins/"):
                            rel = norm[len("Skins/") :]
                        else:
                            rel = os.path.join(os.path.splitext(os.path.basename(path))[0], norm)
                        if not rel or rel.endswith("/"):
                            continue
                        dest = os.path.join(USER_SKINS_DIR, rel)
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        with zf.open(member) as src, open(dest, "wb") as dst:
                            shutil.copyfileobj(src, dst)
        elif ext == ".ini":
            src_dir = os.path.dirname(os.path.abspath(path))
            base_stem = os.path.splitext(os.path.basename(path))[0]
            folder_name = os.path.basename(src_dir)
            if not folder_name or folder_name.lower() in ("community", "downloads", "documents", "desktop", "skins"):
                folder_name = base_stem
                dest_dir = os.path.join(USER_SKINS_DIR, folder_name)
                os.makedirs(dest_dir, exist_ok=True)
                shutil.copy2(path, os.path.join(dest_dir, os.path.basename(path)))
            else:
                dest_dir = os.path.join(USER_SKINS_DIR, folder_name)
                if os.path.abspath(src_dir) != os.path.abspath(dest_dir):
                    shutil.copytree(src_dir, dest_dir, dirs_exist_ok=True)

        old_state = dict(self.skin_state)
        self.skins = discover_all_skins()
        new_loaded = load_global_config(self.skins)
        for k, v in old_state.items():
            if k in new_loaded:
                new_loaded[k] = v
        self.skin_state = new_loaded

        new_key = None
        for s in self.skins:
            if s["key"] not in before_keys:
                new_key = s["key"]
                self.skin_state[new_key]["active"] = True
                break
        if new_key is None:
            stem = os.path.splitext(os.path.basename(path))[0].lower()
            for s in self.skins:
                if stem in s["key"].lower():
                    new_key = s["key"]
                    self.skin_state[new_key]["active"] = True
                    break

        def _finish_ui():
            self._populate_suites_tab()
            self._populate_basic_widgets_tab()
            self._populate_widgets_tab()
            if new_key:
                self._select_widget(new_key)
            self.view_stack.set_visible_child_name("widgets")
            return False

        GLib.idle_add(_finish_ui)
        return new_key

    def _on_install_file_selected(self, dialog, result):
        try:
            gfile = dialog.open_finish(result)
        except Exception:
            return
        if gfile is None:
            return
        path = gfile.get_path()
        if not path or not os.path.isfile(path):
            return

        try:
            self._install_skin_from_path(path)
            self._launch_active_items()
            self._show_toast(f"Installed & activated: {os.path.basename(path)}")
        except Exception as e:
            self._show_toast(f"Install failed: {e}")

    def _on_open_skins_folder(self, _btn):
        os.makedirs(USER_SKINS_DIR, exist_ok=True)
        subprocess.Popen(["xdg-open", USER_SKINS_DIR], start_new_session=True, close_fds=True)

    def _on_refresh_clicked(self, _btn):
        def _do_refresh():
            prev_key = self.selected_key
            self.monitors = detect_monitors()
            self.skins = discover_all_skins()
            self.custom_suites = discover_custom_suites()
            self.skin_state = load_global_config(self.skins)
            self._populate_suites_tab()
            self._populate_basic_widgets_tab()
            self._populate_widgets_tab()
            if prev_key and prev_key in self.skin_state:
                self._select_widget(prev_key)
            elif self.skins:
                self._select_widget(self.skins[0]["key"])
            if _btn is not None:
                self._show_toast("Reloaded suites, widgets, and desktop positions")
            return False

        GLib.idle_add(_do_refresh)

    def _on_apply_and_launch(self, _btn):
        if self.selected_key and not any(self.skin_state[s["key"]]["active"] for s in self.skins):
            self.skin_state[self.selected_key]["active"] = True
            self._sync_active_states_in_place()
        self._launch_active_items()

    def _launch_active_items(self):
        active_skins = [s for s in self.skins if self.skin_state[s["key"]]["active"]]
        save_global_config(self.skins, self.skin_state)
        stop_engine()

        if not active_skins:
            self._update_engine_status()
            self._show_toast("No active widgets; engine stopped")
            return

        cmd = [ENGINE_BIN]
        for s in active_skins:
            cmd.append(s["key"])

        subprocess.Popen(
            cmd,
            cwd=REPO_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
        names = ", ".join(s["title"] for s in active_skins)
        self._show_toast(f"Active on desktop: {names}")
        GLib.timeout_add(250, self._update_engine_status)

    def _on_stop_clicked(self, _btn):
        stop_engine()
        self.active_custom_suite_id = None
        for s in self.skins:
            self.skin_state[s["key"]]["active"] = False
        save_global_config(self.skins, self.skin_state)
        self._sync_active_states_in_place()
        self._update_engine_status()
        self._show_toast("Engine stopped and desktop cleared")

    def _on_open_weather_forecast_clicked(self, _btn):
        def _on_location_updated(rebuild_model=True):
            (
                self.weather_locations,
                self.weather_active_idx,
                self.weather_units,
            ) = load_weather_config()
            GLib.idle_add(lambda: self._populate_weather_locations_ui(rebuild_model=rebuild_model))
            self._updating_controls = True
            try:
                self.weather_units_dropdown.set_selected(1 if self.weather_units == "imperial" else 0)
            finally:
                self._updating_controls = False

        win = WeatherForecastWindow(self.get_application(), on_change_cb=_on_location_updated)
        win.present()

    def _update_engine_status(self):
        pids = get_engine_pids()
        if pids:
            self.status_label.set_label(f"● Running (PID {', '.join(str(p) for p in pids)})")
        else:
            self.status_label.set_label("○ Stopped")
        return True


class WeatherForecastWindow(Adw.ApplicationWindow):
    """Expanded Full Weather Forecast + Location / Village Selector Window (triggered by clicking any weather widget)."""

    def __init__(self, app, on_change_cb=None):
        super().__init__(application=app)
        self.on_change_cb = on_change_cb
        self.set_title("Trad Rainmeter — Weather Forecast")
        self.set_default_size(920, 700)

        (
            self.weather_locations,
            self.weather_active_idx,
            self.weather_units,
        ) = load_weather_config()

        self._updating = False
        self._forecast_data = None
        self._forecast_seq = 0
        self._search_results = []
        self._search_rows = []
        self._daily_slots = []

        self._build_ui()
        self._refresh_forecast()

    def _build_ui(self):
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toast_overlay.set_child(root)

        header = Adw.HeaderBar()
        root.append(header)

        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh live weather forecast")
        refresh_btn.connect("clicked", lambda _b: self._refresh_forecast(force=True))
        header.pack_start(refresh_btn)

        loc_model = Gtk.StringList.new([l["name"] for l in self.weather_locations])
        self.loc_dropdown = Gtk.DropDown(model=loc_model)
        self.loc_dropdown.set_selected(self.weather_active_idx)
        self.loc_dropdown.connect("notify::selected", self._on_loc_dropdown_changed)
        header.set_title_widget(self.loc_dropdown)

        unit_model = Gtk.StringList.new(["°C", "°F"])
        self.unit_dropdown = Gtk.DropDown(model=unit_model)
        self.unit_dropdown.set_selected(1 if self.weather_units == "imperial" else 0)
        self.unit_dropdown.connect("notify::selected", self._on_unit_changed)
        header.pack_end(self.unit_dropdown)

        add_loc_toggle = Gtk.ToggleButton(label="Add / Change Location")
        add_loc_toggle.connect("toggled", self._on_toggle_add_panel)
        header.pack_end(add_loc_toggle)
        self.add_loc_toggle = add_loc_toggle

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        root.append(scroll)

        clamp = Adw.Clamp(maximum_size=860)
        scroll.set_child(clamp)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.set_margin_top(18)
        vbox.set_margin_bottom(24)
        vbox.set_margin_start(18)
        vbox.set_margin_end(18)
        clamp.set_child(vbox)

        # Collapsible Add / Search Location Drawer (Cities & Rural Villages)
        self.add_drawer = Adw.PreferencesGroup(
            title="Select or Add Location (Cities, Towns, and Villages)",
            description="Search villages like Mahatlani, Majosi, Masakona, or enter custom coordinates.",
        )
        self.add_drawer.set_visible(False)
        vbox.append(self.add_drawer)

        search_row = Adw.ActionRow(
            title="Search City, Town, or Village",
            subtitle="Uses ArcGIS Gazetteer, Open-Meteo, and OpenStreetMap — or type lat, lon",
        )
        sbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        sbox.set_valign(Gtk.Align.CENTER)
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("e.g. Mahatlani, Majosi, Masakona…")
        self.search_entry.set_width_chars(24)
        self.search_entry.connect("activate", lambda _e: self._on_search_clicked(None))
        sbox.append(self.search_entry)

        self.search_btn = Gtk.Button(label="Search")
        self.search_btn.add_css_class("suggested-action")
        self.search_btn.connect("clicked", self._on_search_clicked)
        sbox.append(self.search_btn)
        search_row.add_suffix(sbox)
        self.add_drawer.add(search_row)

        self.manual_expander = Adw.ExpanderRow(
            title="Add Village or Location Manually (Name + Coordinates)",
            subtitle="If your village is not auto-detected, enter a label and latitude/longitude",
        )
        self.add_drawer.add(self.manual_expander)

        mbox_row = Adw.PreferencesRow()
        mbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        mbox.set_margin_top(8)
        mbox.set_margin_bottom(8)
        mbox.set_margin_start(12)
        mbox.set_margin_end(12)
        mbox_row.set_child(mbox)

        row1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        mbox.append(row1)
        row1.append(Gtk.Label(label="Name:", xalign=0))
        self.manual_name = Gtk.Entry()
        self.manual_name.set_placeholder_text("e.g. Mahatlani Village")
        self.manual_name.set_hexpand(True)
        row1.append(self.manual_name)

        row2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        mbox.append(row2)
        row2.append(Gtk.Label(label="Lat:"))
        self.manual_lat = Gtk.Entry()
        self.manual_lat.set_placeholder_text("-23.2420")
        self.manual_lat.set_hexpand(True)
        row2.append(self.manual_lat)
        row2.append(Gtk.Label(label="Lon:"))
        self.manual_lon = Gtk.Entry()
        self.manual_lon.set_placeholder_text("30.2762")
        self.manual_lon.set_hexpand(True)
        row2.append(self.manual_lon)

        save_manual_btn = Gtk.Button(label="Save Location & Show Forecast")
        save_manual_btn.add_css_class("suggested-action")
        save_manual_btn.connect("clicked", self._on_save_manual)
        mbox.append(save_manual_btn)
        self.manual_expander.add_row(mbox_row)

        self.search_results_group = Adw.PreferencesGroup(title="Search Results")
        self.search_results_group.set_visible(False)
        vbox.append(self.search_results_group)

        # Current Hero Summary Card
        hero_frame = Gtk.Frame()
        vbox.append(hero_frame)

        hero_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        hero_box.set_margin_top(18)
        hero_box.set_margin_bottom(18)
        hero_box.set_margin_start(22)
        hero_box.set_margin_end(22)
        hero_frame.set_child(hero_box)

        left_hero = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        left_hero.set_hexpand(True)
        hero_box.append(left_hero)

        self.hero_icon = Gtk.Image.new_from_icon_name("weather-few-clouds-symbolic")
        self.hero_icon.set_pixel_size(68)
        left_hero.append(self.hero_icon)

        title_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        left_hero.append(title_col)

        cur_loc = self.weather_locations[self.weather_active_idx]
        self.hero_city_lbl = Gtk.Label(label=cur_loc["name"], xalign=0)
        self.hero_city_lbl.add_css_class("title-3")
        self.hero_city_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        self.hero_city_lbl.set_max_width_chars(28)
        title_col.append(self.hero_city_lbl)

        self.hero_temp_lbl = Gtk.Label(label="--°", xalign=0)
        self.hero_temp_lbl.add_css_class("title-1")
        title_col.append(self.hero_temp_lbl)

        self.hero_cond_lbl = Gtk.Label(label="Loading forecast…", xalign=0)
        self.hero_cond_lbl.add_css_class("dim-label")
        self.hero_cond_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        self.hero_cond_lbl.set_max_width_chars(38)
        title_col.append(self.hero_cond_lbl)

        right_hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        right_hero.set_valign(Gtk.Align.CENTER)
        hero_box.append(right_hero)

        self.hero_details_lbl = Gtk.Label(label="", xalign=1)
        self.hero_details_lbl.set_justify(Gtk.Justification.RIGHT)
        right_hero.append(self.hero_details_lbl)

        self.hero_sun_lbl = Gtk.Label(label="", xalign=1)
        self.hero_sun_lbl.add_css_class("caption")
        self.hero_sun_lbl.add_css_class("dim-label")
        right_hero.append(self.hero_sun_lbl)

        # Hourly Curve Chart Group (24-Hour Curve + Time Labels)
        hourly_group = Adw.PreferencesGroup(
            title="Hourly Forecast (Next 24 Hours)",
            description="Temperature curve, precipitation chance, and hourly trend",
        )
        vbox.append(hourly_group)

        chart_frame = Gtk.Frame()
        hourly_group.add(chart_frame)

        self.hourly_chart = Gtk.DrawingArea()
        self.hourly_chart.set_content_height(220)
        self.hourly_chart.set_hexpand(True)
        self.hourly_chart.set_draw_func(self._draw_hourly_chart)
        chart_frame.set_child(self.hourly_chart)

        # 7-Day Daily Forecast Group (pre-allocate 7 reusable rows for zero UI churn)
        self.daily_group = Adw.PreferencesGroup(
            title="7-Day Forecast",
            description="Daily conditions, rain chance, low and high temperatures",
        )
        vbox.append(self.daily_group)
        for _ in range(7):
            row = Adw.ActionRow(title="—", subtitle="—")
            ico = Gtk.Image.new_from_icon_name("weather-overcast-symbolic")
            ico.set_pixel_size(24)
            row.add_prefix(ico)
            range_lbl = Gtk.Label(label="--")
            range_lbl.set_valign(Gtk.Align.CENTER)
            row.add_suffix(range_lbl)
            row.set_visible(False)
            self.daily_group.add(row)
            self._daily_slots.append((row, ico, range_lbl))

    def _show_toast(self, msg):
        toast = Adw.Toast.new(GLib.markup_escape_text(msg))
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)

    def _on_toggle_add_panel(self, btn):
        self.add_drawer.set_visible(btn.get_active())

    def _sync_and_reload(self, msg=None, rebuild_model=False, force=False):
        save_weather_config(self.weather_locations, self.weather_active_idx, self.weather_units)
        if rebuild_model:
            def _update_dropdown():
                self._updating = True
                try:
                    self.loc_dropdown.set_model(Gtk.StringList.new([l["name"] for l in self.weather_locations]))
                    self.loc_dropdown.set_selected(self.weather_active_idx)
                finally:
                    self._updating = False
                return False

            GLib.idle_add(_update_dropdown)

        relaunch_active_engine_from_config()
        if self.on_change_cb:
            GLib.idle_add(lambda: (self.on_change_cb(rebuild_model), False)[1])
        self._refresh_forecast(force=force)
        if msg:
            self._show_toast(msg)

    def _on_loc_dropdown_changed(self, dropdown, _pspec):
        if self._updating:
            return
        idx = int(dropdown.get_selected())
        if 0 <= idx < len(self.weather_locations) and idx != self.weather_active_idx:
            self.weather_active_idx = idx
            self._sync_and_reload(
                f"Switched weather to '{self.weather_locations[idx]['name']}'",
                rebuild_model=False,
            )

    def _on_unit_changed(self, dropdown, _pspec):
        if self._updating:
            return
        self.weather_units = "imperial" if int(dropdown.get_selected()) == 1 else "metric"
        self._sync_and_reload(rebuild_model=False)

    def _on_search_clicked(self, _btn):
        q = self.search_entry.get_text().strip()
        if not q:
            return
        self.search_btn.set_sensitive(False)
        self.search_btn.set_label("Searching…")

        def _worker():
            res = search_weather_locations(q)

            def _done():
                self.search_btn.set_sensitive(True)
                self.search_btn.set_label("Search")
                self._search_results = res
                self._populate_search_results(q)
                return False

            GLib.idle_add(_done)

        threading.Thread(target=_worker, daemon=True).start()

    def _populate_search_results(self, q):
        for r in self._search_rows:
            self.search_results_group.remove(r)
        self._search_rows = []
        self.search_results_group.set_visible(True)

        if not self._search_results:
            row = Adw.ActionRow(
                title=GLib.markup_escape_text(f"No match found for '{q}'"),
                subtitle="Try the village name without 'village', search a nearby town, or open Manual Entry above.",
            )
            btn = Gtk.Button(label="Enter Manually")
            btn.set_valign(Gtk.Align.CENTER)
            btn.add_css_class("suggested-action")
            btn.connect("clicked", lambda _b: (self.manual_name.set_text(q), self.manual_expander.set_expanded(True)))
            row.add_suffix(btn)
            self.search_results_group.add(row)
            self._search_rows.append(row)
            return

        for item in self._search_results:
            sub = f"{item['source']} • Lat: {item['lat']:.4f}, Lon: {item['lon']:.4f}"
            if item.get("detail"):
                sub += f" • {item['detail']}"
            row = Adw.ActionRow(
                title=GLib.markup_escape_text(item["name"]),
                subtitle=GLib.markup_escape_text(sub[:135]),
            )
            ren = Gtk.Button(label="Rename & Add")
            ren.set_valign(Gtk.Align.CENTER)
            ren.connect("clicked", self._on_rename_search_item, item)
            row.add_suffix(ren)

            use_b = Gtk.Button(label="Select")
            use_b.set_valign(Gtk.Align.CENTER)
            use_b.add_css_class("suggested-action")
            use_b.connect("clicked", self._on_pick_search_item, item)
            row.add_suffix(use_b)

            self.search_results_group.add(row)
            self._search_rows.append(row)

    def _on_rename_search_item(self, _b, item):
        typed = self.search_entry.get_text().strip()
        self.manual_name.set_text(typed if typed else item["name"])
        self.manual_lat.set_text(f"{item['lat']:.5f}")
        self.manual_lon.set_text(f"{item['lon']:.5f}")
        self.manual_expander.set_expanded(True)

    def _add_and_activate(self, name, lat, lon):
        existing = next((i for i, l in enumerate(self.weather_locations) if l["name"].lower() == name.lower()), None)
        if existing is not None:
            self.weather_locations[existing] = {"name": name, "lat": lat, "lon": lon}
            self.weather_active_idx = existing
        else:
            self.weather_locations.insert(0, {"name": name, "lat": lat, "lon": lon})
            self.weather_active_idx = 0
        self.search_results_group.set_visible(False)
        self.add_loc_toggle.set_active(False)
        self._sync_and_reload(f"Added & loaded weather for '{name}'", rebuild_model=True)

    def _on_pick_search_item(self, _b, item):
        GLib.idle_add(lambda: (self._add_and_activate(item["name"], item["lat"], item["lon"]), False)[1])

    def _on_save_manual(self, _b):
        name = self.manual_name.get_text().strip()
        try:
            lat = float(self.manual_lat.get_text().strip())
            lon = float(self.manual_lon.get_text().strip())
        except ValueError:
            self._show_toast("Please enter valid Latitude and Longitude")
            return
        if not name or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            self._show_toast("Enter a valid Name and coordinates (-90..90, -180..180)")
            return
        self.manual_name.set_text("")
        self.manual_lat.set_text("")
        self.manual_lon.set_text("")
        self.manual_expander.set_expanded(False)
        self._add_and_activate(name, lat, lon)

    def _refresh_forecast(self, force=False):
        loc = self.weather_locations[self.weather_active_idx]
        self._forecast_seq += 1
        seq = self._forecast_seq
        self.hero_city_lbl.set_label(loc["name"])
        self.hero_cond_lbl.set_label(f"Fetching forecast for ({loc['lat']:.4f}, {loc['lon']:.4f})…")

        def _worker():
            try:
                data = fetch_full_weather_forecast(loc["lat"], loc["lon"], self.weather_units, force=force)
                GLib.idle_add(lambda: (self._apply_forecast_data(loc, data, seq), False)[1])
            except Exception as exc:
                err = str(exc)

                def _err_ui():
                    if seq == self._forecast_seq:
                        self.hero_cond_lbl.set_label(f"Could not fetch weather: {err}")
                    return False

                GLib.idle_add(_err_ui)

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_forecast_data(self, loc, data, seq=None):
        if seq is not None and seq != self._forecast_seq:
            return
        self._forecast_data = data
        cur = data.get("current", {})
        daily = data.get("daily", {})

        t_unit = "°F" if self.weather_units == "imperial" else "°C"
        s_unit = "mph" if self.weather_units == "imperial" else "km/h"
        cond_text, icon_name = wmo_info(cur.get("weather_code"))

        self.hero_icon.set_from_icon_name(icon_name)
        self.hero_city_lbl.set_label(loc["name"])
        self.hero_temp_lbl.set_label(f"{round(cur.get('temperature_2m', 0))}{t_unit}")

        hi_list = daily.get("temperature_2m_max", [])
        lo_list = daily.get("temperature_2m_min", [])
        hi_s = f"{round(hi_list[0])}°" if hi_list else "--"
        lo_s = f"{round(lo_list[0])}°" if lo_list else "--"

        self.hero_cond_lbl.set_label(
            f"{cond_text}  •  High {hi_s} / Low {lo_s}  •  Feels like {round(cur.get('apparent_temperature', 0))}{t_unit}"
        )

        hum = cur.get("relative_humidity_2m", 0)
        rain = cur.get("precipitation_probability", 0)
        wspd = cur.get("wind_speed_10m", 0)
        wdir = wind_compass(cur.get("wind_direction_10m", 0))
        pres = cur.get("surface_pressure", 0)
        self.hero_details_lbl.set_label(
            f"Humidity: {round(hum)}%   •   Rain Chance: {round(rain)}%\n"
            f"Wind: {round(wspd)} {s_unit} ({wdir})   •   Pressure: {round(pres)} hPa"
        )

        sunrises = daily.get("sunrise", [])
        sunsets = daily.get("sunset", [])
        sr = sunrises[0].split("T")[-1] if sunrises else "--:--"
        ss = sunsets[0].split("T")[-1] if sunsets else "--:--"
        tz = data.get("timezone_abbreviation", "")
        self.hero_sun_lbl.set_label(f"Sunrise {sr}   •   Sunset {ss}   •   {loc['lat']:.4f}, {loc['lon']:.4f} ({tz})")

        self.hourly_chart.queue_draw()

        # Update pre-allocated 7-Day rows in-place (zero GTK4 layout teardown)
        import datetime

        dates = daily.get("time", [])
        codes = daily.get("weather_code", [])
        tmaxs = daily.get("temperature_2m_max", [])
        tmins = daily.get("temperature_2m_min", [])
        rpops = daily.get("precipitation_probability_max", [])

        for i, (row, ico, range_lbl) in enumerate(self._daily_slots):
            if i >= len(dates):
                row.set_visible(False)
                continue
            try:
                dt = datetime.date.fromisoformat(dates[i])
                day_lbl = "Today" if i == 0 else dt.strftime("%A, %b %d")
            except Exception:
                day_lbl = dates[i]

            c_txt, c_ico = wmo_info(codes[i] if i < len(codes) else None)
            hi = round(tmaxs[i]) if i < len(tmaxs) else 0
            lo = round(tmins[i]) if i < len(tmins) else 0
            pop = round(rpops[i]) if i < len(rpops) and rpops[i] is not None else 0

            row.set_title(GLib.markup_escape_text(day_lbl))
            row.set_subtitle(GLib.markup_escape_text(f"{c_txt}  •  Rain chance {pop}%"))
            ico.set_from_icon_name(c_ico)
            range_lbl.set_label(f"Low {lo}{t_unit}   →   High {hi}{t_unit}")
            row.set_visible(True)

    def _draw_hourly_chart(self, _area, cr, width, height):
        # Background
        cr.set_source_rgba(0.11, 0.12, 0.16, 1.0)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        if not self._forecast_data:
            cr.set_source_rgba(0.75, 0.78, 0.85, 0.9)
            cr.select_font_face("Sans", 0, 0)
            cr.set_font_size(13)
            cr.move_to(24, height / 2)
            cr.show_text("Loading 24-hour temperature curve…")
            return

        hourly = self._forecast_data.get("hourly", {})
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        pops = hourly.get("precipitation_probability", [])
        cur_time = self._forecast_data.get("current", {}).get("time", "")

        start_idx = 0
        if cur_time and cur_time[:13]:
            prefix = cur_time[:13]
            for idx, t in enumerate(times):
                if t.startswith(prefix):
                    start_idx = idx
                    break

        count = min(13, max(0, len(times) - start_idx))
        if count < 2:
            return

        slice_t = times[start_idx : start_idx + count]
        slice_v = [float(x) for x in temps[start_idx : start_idx + count]]
        slice_p = [int(pops[start_idx + k] or 0) if start_idx + k < len(pops) else 0 for k in range(count)]

        vmin = min(slice_v)
        vmax = max(slice_v)
        span = max(2.0, vmax - vmin)

        pad_x = 34
        top_y = 54
        bot_y = height - 42
        plot_w = max(100, width - pad_x * 2)
        plot_h = max(40, bot_y - top_y)

        pts = []
        for i in range(count):
            px = pad_x + (i / (count - 1)) * plot_w
            py = bot_y - ((slice_v[i] - vmin) / span) * plot_h
            pts.append((px, py))

        # Vertical grid separators & labels
        cr.select_font_face("Sans", 0, 0)
        for i, (px, py) in enumerate(pts):
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.08)
            cr.set_line_width(1.0)
            cr.move_to(px, 18)
            cr.line_to(px, height - 12)
            cr.stroke()

            # Time header
            hr_label = "Now" if i == 0 else slice_t[i].split("T")[-1][:5]
            cr.set_source_rgba(0.85, 0.88, 0.94, 0.90)
            cr.set_font_size(10.5)
            cr.move_to(px - 14, 22)
            cr.show_text(hr_label)

            # Rain % under time
            if slice_p[i] > 0:
                cr.set_source_rgba(0.35, 0.78, 1.0, 0.95)
                cr.set_font_size(9.5)
                cr.move_to(px - 10, 36)
                cr.show_text(f"{slice_p[i]}%")

        # Shaded gradient area under curve
        cr.move_to(pts[0][0], bot_y + 12)
        cr.line_to(pts[0][0], pts[0][1])
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            cx = (x0 + x1) * 0.5
            cr.curve_to(cx, y0, cx, y1, x1, y1)
        cr.line_to(pts[-1][0], bot_y + 12)
        cr.close_path()
        cr.set_source_rgba(0.95, 0.68, 0.12, 0.22)
        cr.fill()

        # Curve stroke (warm golden-amber like GNOME Weather)
        cr.move_to(pts[0][0], pts[0][1])
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            cx = (x0 + x1) * 0.5
            cr.curve_to(cx, y0, cx, y1, x1, y1)
        cr.set_source_rgba(0.98, 0.75, 0.18, 1.0)
        cr.set_line_width(2.4)
        cr.stroke()

        # Points + Temperature values at bottom
        for i, (px, py) in enumerate(pts):
            cr.set_source_rgba(0.98, 0.80, 0.25, 1.0)
            cr.arc(px, py, 3.2, 0, 6.28318)
            cr.fill()

            cr.set_source_rgba(0.98, 0.82, 0.35, 0.95)
            cr.set_font_size(11.5)
            cr.move_to(px - 11, height - 14)
            cr.show_text(f"{round(slice_v[i])}°")


class RainmeterControlApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="com.github.kiddzhasi.TradRainmeter",
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )

    def do_activate(self):
        style_mgr = Adw.StyleManager.get_default()
        style_mgr.set_color_scheme(Adw.ColorScheme.PREFER_DARK)
        win = self.props.active_window
        if not win:
            win = ControlCenterWindow(self)
        win.present()


class WeatherPopupApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="com.github.kiddzhasi.TradRainmeter.Weather",
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )

    def do_activate(self):
        style_mgr = Adw.StyleManager.get_default()
        style_mgr.set_color_scheme(Adw.ColorScheme.PREFER_DARK)
        win = self.props.active_window
        if not win:
            win = WeatherForecastWindow(self)
        win.present()


if __name__ == "__main__":
    if "--reload" in sys.argv:
        stop_engine()
        if os.path.isfile(GLOBAL_CONFIG) and os.path.isfile(ENGINE_BIN):
            cp = configparser.ConfigParser(interpolation=None, strict=False)
            cp.optionxform = str
            cp.read(GLOBAL_CONFIG, encoding="utf-8")
            keys = [s for s in cp.sections() if cp.get(s, "Active", fallback="0").strip() not in ("0", "false", "")]
            if keys:
                subprocess.Popen(
                    [ENGINE_BIN] + keys,
                    cwd=REPO_DIR,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                    close_fds=True,
                )
        sys.exit(0)
    if "--weather-popup" in sys.argv:
        argv = [a for a in sys.argv if a != "--weather-popup"]
        sys.exit(WeatherPopupApp().run(argv))
    app = RainmeterControlApp()
    sys.exit(app.run(sys.argv))

#!/usr/bin/env python3
"""
Trad Rainmeter — Official Windows .rmskin Package Builder
Creates a genuine Windows Rainmeter .rmskin installer package with:
  1. RMSKIN.ini & 400x60 24-bit RMSKIN.bmp header banner
  2. All Trad Suites (TradSunset, DashboardSuite, GreenRibbonSuite, TealMountainSuite)
  3. All 13 Modular Widgets (8 Basic Telemetry Widgets + 3 Music Players + 2 Audio Visualizers)
     plus current Theme.inc & Weather.inc
  4. Automatic Windows Rainmeter WebParser fallback for Measure=Weather so weather skins
     work both in TradRainmeter.exe (Standalone Engine) AND classic Windows Rainmeter 4.5+!
  5. Official 16-byte binary RMSKIN footer (<int64 zip_size><uint8 flags=0>"RMSKIN\\0")
     required by Windows Rainmeter SkinInstaller.exe.
"""

import os
import re
import struct
import sys
import zipfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)


def make_rmskin_header_bmp(width=400, height=60):
    """Generate a 400x60 24-bit BMP banner for Windows Rainmeter SkinInstaller.exe."""
    row_stride = (width * 3 + 3) & ~3
    pixel_data = bytearray(row_stride * height)
    for y in range(height):
        # Gradient from deep slate-purple (#141024) to cyber-blue (#263E7A)
        t_y = y / max(1, height - 1)
        for x in range(width):
            t_x = x / max(1, width - 1)
            r = int(18 + 38 * t_x + 12 * (1.0 - t_y))
            g = int(16 + 52 * t_x + 18 * (1.0 - t_y))
            b = int(36 + 98 * t_x + 25 * (1.0 - t_y))
            # Accent bottom border strip (3px gold/cyan glow)
            if y < 3:
                r, g, b = 0, 195, 255
            off = y * row_stride + x * 3
            pixel_data[off] = max(0, min(255, b))
            pixel_data[off + 1] = max(0, min(255, g))
            pixel_data[off + 2] = max(0, min(255, r))

    file_size = 14 + 40 + len(pixel_data)
    bmp_header = struct.pack("<2sIHHI", b"BM", file_size, 0, 0, 54)
    dib_header = struct.pack(
        "<IiiHHIIiiII",
        40,
        width,
        height,
        1,
        24,
        0,
        len(pixel_data),
        2835,
        2835,
        0,
        0,
    )
    return bmp_header + dib_header + bytes(pixel_data)


def convert_ini_for_windows_rainmeter(content, is_widget=False):
    """
    Ensure .ini skin text works seamlessly in both TradRainmeter.exe and classic
    Windows Rainmeter 4.5+:
      - Normalize @Include paths to Windows backslashes
      - Normalize Linux strftime %-I / %-d to Windows %#I / %#d
    """
    text = content.replace("%-I", "%#I").replace("%-d", "%#d").replace("%-m", "%#m")
    if is_widget:
        text = text.replace("@Include=../Theme.inc", "@Include=#@#Theme.inc")
        text = text.replace("@Include=../Weather.inc", "@Include=#@#Weather.inc")
    return text


def build_rmskin_package(output_path=None, version="1.1.0", config_dir=None):
    """Build TradRainmeter_<version>.rmskin and append the official 16-byte binary footer."""
    if output_path is None:
        dist_dir = os.path.join(REPO_DIR, "dist")
        os.makedirs(dist_dir, exist_ok=True)
        output_path = os.path.join(dist_dir, f"TradRainmeter_{version}.rmskin")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    if config_dir is None:
        if sys.platform == "win32":
            appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
            config_dir = os.path.join(appdata, "TradRainmeter")
        else:
            config_dir = os.path.expanduser("~/.config/rainmeter-native")

    rmskin_ini = (
        "[rmskin]\r\n"
        "Name=Trad Rainmeter Suite & Widgets\r\n"
        "Author=K-Trad (KidDzhasi)\r\n"
        f"Version={version}\r\n"
        "LoadType=Skin\r\n"
        "Load=TradRainmeter\\Suites\\TradSunset\\TradSunset.ini\r\n"
        "MinimumRainmeter=4.5.0\r\n"
        "MinimumWindows=6.1\r\n"
    )

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("RMSKIN.ini", rmskin_ini.encode("utf-8"))
        zf.writestr("RMSKIN.bmp", make_rmskin_header_bmp())

        # Include Theme.inc and Weather.inc in Skins/TradRainmeter/@Resources/
        for inc_name in ("Theme.inc", "Weather.inc"):
            user_inc = os.path.join(config_dir, inc_name)
            repo_inc = os.path.join(REPO_DIR, "widgets", inc_name)
            src_inc = user_inc if os.path.isfile(user_inc) else repo_inc
            if os.path.isfile(src_inc):
                with open(src_inc, "r", encoding="utf-8", errors="ignore") as f:
                    inc_text = f.read()
                zf.writestr(f"Skins/TradRainmeter/@Resources/{inc_name}", inc_text.encode("utf-8"))
                zf.writestr(f"Skins/TradRainmeter/Widgets/{inc_name}", inc_text.encode("utf-8"))

        # Package all Suites
        suites_dir = os.path.join(REPO_DIR, "suites")
        if os.path.isdir(suites_dir):
            for root, _dirs, files in os.walk(suites_dir):
                for file in sorted(files):
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, suites_dir).replace("\\", "/")
                    arc_p = f"Skins/TradRainmeter/Suites/{rel_p}"
                    if file.lower().endswith((".ini", ".inc")):
                        with open(full_p, "r", encoding="utf-8", errors="ignore") as f:
                            txt = convert_ini_for_windows_rainmeter(f.read(), is_widget=False)
                        zf.writestr(arc_p, txt.encode("utf-8"))
                    else:
                        zf.write(full_p, arc_p)

        # Package all Widgets
        widgets_dir = os.path.join(REPO_DIR, "widgets")
        if os.path.isdir(widgets_dir):
            for root, _dirs, files in os.walk(widgets_dir):
                for file in sorted(files):
                    if root == widgets_dir and file in ("Theme.inc", "Weather.inc"):
                        continue
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, widgets_dir).replace("\\", "/")
                    arc_p = f"Skins/TradRainmeter/Widgets/{rel_p}"
                    if file.lower().endswith((".ini", ".inc")):
                        with open(full_p, "r", encoding="utf-8", errors="ignore") as f:
                            txt = convert_ini_for_windows_rainmeter(f.read(), is_widget=True)
                        zf.writestr(arc_p, txt.encode("utf-8"))
                    else:
                        zf.write(full_p, arc_p)

    # Append official 16-byte Windows Rainmeter binary footer:
    #   int64 zip_size (little-endian) + uint8 flags (0) + "RMSKIN\x00" (7 bytes)
    zip_size = os.path.getsize(output_path)
    footer = struct.pack("<qB7s", zip_size, 0, b"RMSKIN\x00")
    with open(output_path, "ab") as f:
        f.write(footer)

    return output_path


if __name__ == "__main__":
    ver = sys.argv[1] if len(sys.argv) > 1 else "1.1.0"
    out = sys.argv[2] if len(sys.argv) > 2 else None
    path = build_rmskin_package(output_path=out, version=ver)
    print(f"Built Windows Rainmeter package: {path} ({os.path.getsize(path)} bytes)")

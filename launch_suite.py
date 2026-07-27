#!/usr/bin/env python3
import os
import glob
import subprocess

# List all the specific folders where your custom suites live
custom_folders = [
    os.path.expanduser("~/.config/rainmeter-native/Skins/PopNative"),
    os.path.expanduser("~/Documents/GitHub/rainmeter-native/community"),
    os.path.expanduser("~/Documents/GitHub/rainmeter-native/suites")
]

ini_files = []
for folder in custom_folders:
    if os.path.exists(folder):
        ini_files.extend(glob.glob(os.path.join(folder, "**/*.ini"), recursive=True))

if not ini_files:
    print("No custom configurations found in your designated folders.")
    exit(1)

print("========================================")
print("      CUSTOM DASHBOARD SELECTOR")
print("========================================")
for idx, ini in enumerate(ini_files):
    # Clean up the display name to show the parent directories (e.g., suites/TradSunset/TradSunset.ini)
    parts = ini.split(os.sep)
    display_name = "/".join(parts[-3:]) if len(parts) >= 3 else os.path.basename(ini)
    print(f"  [{idx + 1}] {display_name}")
print("========================================")

try:
    choice = int(input("\nEnter the number of the custom suite you want to load: ")) - 1
    if 0 <= choice < len(ini_files):
        selected_ini = ini_files[choice]
        print(f"\n[+] Loading Custom Dashboard: {selected_ini}")
        
        # Stop any currently running engine instance
        os.system("killall -9 rainmeter-native 2>/dev/null")
        
        # Path to your compiled binary
        binary_path = os.path.expanduser("~/Documents/GitHub/rainmeter-native/build/rainmeter-native")
        
        if not os.path.exists(binary_path):
            print("[-] Error: rainmeter-native binary not found in build/. Please compile first.")
            exit(1)
            
        # Launch the selected suite detached in the background
        subprocess.Popen([binary_path, selected_ini], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[✓] Custom suite launched successfully!")
    else:
        print("[-] Invalid selection number.")
except ValueError:
    print("[-] Please enter a valid integer.")

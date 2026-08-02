#!/usr/bin/env python3
import os
import subprocess
import time

# --- Configuration Paths ---
REPO_DIR = os.path.expanduser("~/Documents/GitHub/rainmeter-native")
BUILD_DIR = os.path.join(REPO_DIR, "build")
GLOBAL_CONFIG = os.path.expanduser("~/.config/rainmeter-native/Rainmeter.ini")

def get_connected_monitors():
    """Detect the number of connected monitors by checking the Linux DRM subsystem."""
    count = 0
    try:
        drm_path = '/sys/class/drm'
        if os.path.exists(drm_path):
            for item in os.listdir(drm_path):
                # Look for graphics cards with output ports (e.g., card0-DP-1, card0-HDMI-A-1)
                if item.startswith('card') and '-' in item:
                    status_file = os.path.join(drm_path, item, 'status')
                    if os.path.exists(status_file):
                        with open(status_file, 'r') as f:
                            if f.read().strip() == 'connected':
                                count += 1
    except Exception as e:
        print(f"Monitor detection warning: {e}")
    
    # Always default to at least 1 monitor if the sysfs check fails
    return max(1, count)

def get_github_skins():
    """Dynamically scan the confirmed GitHub 'suites' directory."""
    skins = []
    suites_dir = os.path.join(REPO_DIR, "suites")
    if os.path.exists(suites_dir):
        # Sort folders alphabetically
        for folder in sorted(os.listdir(suites_dir)):
            ini_path = os.path.join(suites_dir, folder, f"{folder}.ini")
            if os.path.exists(ini_path):
                skins.append(f"suites/{folder}/{folder}.ini")
    return skins

def kill_engine():
    """Find and terminate any running instances of the C++ engine."""
    subprocess.run(["pkill", "-x", "rainmeter-native"], stderr=subprocess.DEVNULL)

def main():
    print("========================================")
    print("      CUSTOM DASHBOARD SELECTOR")
    print("========================================")
    
    # Option to turn off the UI entirely
    print("  [0] Turn OFF active skins (Kill Engine)")
    
    # Dynamically list only the confirmed skins
    skins = get_github_skins()
    for i, skin in enumerate(skins, start=1):
        print(f"  [{i}] {skin}")
        
    print("========================================")
    
    try:
        choice = int(input("\nEnter the number of the option you want: "))
    except ValueError:
        print("[!] Invalid input. Please enter a number.")
        return

    # Handle Kill Switch
    if choice == 0:
        print("\n[+] Stopping rainmeter-native engine...")
        kill_engine()
        print("[✓] Engine stopped. Desktop is clear.")
        return
        
    if choice < 1 or choice > len(skins):
        print("[!] Invalid selection.")
        return
        
    selected_skin = skins[choice - 1]
    
    # Monitor Detection & Selection
    num_monitors = get_connected_monitors()
    print(f"\n[+] Detected {num_monitors} connected monitor(s).")
    
    for m in range(num_monitors):
        print(f"  [{m}] Monitor {m}")
        
    try:
        monitor_choice = int(input("Select target monitor number: "))
        if monitor_choice < 0 or monitor_choice >= num_monitors:
            print(f"[!] Invalid monitor index. Defaulting to Monitor 0.")
            monitor_choice = 0
    except ValueError:
        print("[!] Invalid input. Defaulting to Monitor 0.")
        monitor_choice = 0

    # Write to Global Config
    print(f"\n[+] Applying configuration for: {selected_skin}")
    try:
        os.makedirs(os.path.dirname(GLOBAL_CONFIG), exist_ok=True)
        with open(GLOBAL_CONFIG, "w") as f:
            f.write(f"[{selected_skin}]\nActive=1\n")
    except IOError as e:
        print(f"[!] Failed to write to config: {e}")
        return

    # Restart Engine as a background process
    kill_engine()
    time.sleep(0.5) # Give the OS half a second to free the Wayland layer surface
    
    print(f"[+] Launching Wayland engine on Monitor {monitor_choice}...")
    os.chdir(BUILD_DIR)
    subprocess.Popen(
        ["./rainmeter-native", "-m", str(monitor_choice)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    print("[✓] Custom suite launched successfully!")

if __name__ == "__main__":
    main()

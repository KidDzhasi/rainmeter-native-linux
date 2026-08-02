#!/usr/bin/env python3
import os
import subprocess
import time
import customtkinter as ctk
from tkinter import messagebox

# --- Configuration Paths ---
REPO_DIR = os.path.expanduser("~/Documents/GitHub/rainmeter-native")
BUILD_DIR = os.path.join(REPO_DIR, "build")
GLOBAL_CONFIG = os.path.expanduser("~/.config/rainmeter-native/Rainmeter.ini")
SUITES_DIR = os.path.join(REPO_DIR, "suites")

def get_connected_monitors():
    count = 0
    try:
        drm_path = '/sys/class/drm'
        if os.path.exists(drm_path):
            for item in os.listdir(drm_path):
                if item.startswith('card') and '-' in item:
                    status_file = os.path.join(drm_path, item, 'status')
                    if os.path.exists(status_file):
                        with open(status_file, 'r') as f:
                            if f.read().strip() == 'connected':
                                count += 1
    except Exception:
        pass
    return max(1, count)

def get_github_skins():
    skins = []
    if os.path.exists(SUITES_DIR):
        for folder in sorted(os.listdir(SUITES_DIR)):
            ini_path = os.path.join(SUITES_DIR, folder, f"{folder}.ini")
            if os.path.exists(ini_path):
                skins.append(f"suites/{folder}/{folder}.ini")
    return skins

def kill_engine():
    subprocess.run(["killall", "rainmeter-native"], stderr=subprocess.DEVNULL)

# --- UI Setup ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class RainmeterLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Rainmeter Native Engine")
        self.geometry("500x380")
        self.resizable(False, False)
        
        self.create_widgets()
        self.populate_data()

    def create_widgets(self):
        # Header
        self.header = ctk.CTkLabel(self, text="Wayland Dashboard Selector", font=ctk.CTkFont(size=20, weight="bold"))
        self.header.pack(pady=(20, 20))

        # Skin Dropdown & Refresh Button
        self.skin_label = ctk.CTkLabel(self, text="Select Active Suite:", anchor="w")
        self.skin_label.pack(padx=40, fill="x")
        
        self.skin_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.skin_frame.pack(padx=40, pady=(0, 15), fill="x")
        
        self.skin_dropdown = ctk.CTkOptionMenu(self.skin_frame, dynamic_resizing=False)
        self.skin_dropdown.pack(side="left", expand=True, fill="x", padx=(0, 10))
        
        self.refresh_btn = ctk.CTkButton(self.skin_frame, text="🔄 Refresh", width=70, command=self.populate_data)
        self.refresh_btn.pack(side="right")

        # Monitor Dropdown
        self.monitor_label = ctk.CTkLabel(self, text="Target Monitor:", anchor="w")
        self.monitor_label.pack(padx=40, fill="x")
        self.monitor_dropdown = ctk.CTkOptionMenu(self, dynamic_resizing=False)
        self.monitor_dropdown.pack(padx=40, pady=(0, 25), fill="x")

        # Action Buttons Frame
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(padx=40, fill="x")

        self.launch_btn = ctk.CTkButton(self.btn_frame, text="Launch", command=self.launch_suite)
        self.launch_btn.pack(side="left", expand=True, padx=(0, 5), fill="x")

        self.kill_btn = ctk.CTkButton(self.btn_frame, text="Turn OFF", fg_color="#b23b3b", hover_color="#8c2a2a", command=self.kill_suite)
        self.kill_btn.pack(side="right", expand=True, padx=(5, 0), fill="x")
        
        # Add Skins Button
        self.add_skins_btn = ctk.CTkButton(self, text="📂 Open Custom Skins Folder", fg_color="transparent", border_width=1, command=self.open_skins_folder)
        self.add_skins_btn.pack(pady=(20, 0), padx=40, fill="x")

    def populate_data(self):
        # Save current selection if possible
        current_skin = self.skin_dropdown.get()
        
        skins = get_github_skins()
        if skins:
            self.skin_dropdown.configure(values=skins)
            # If the user just added a new skin, auto-select it
            if current_skin not in skins and current_skin != "No suites found!":
                self.skin_dropdown.set(skins[-1])
            elif current_skin in skins:
                self.skin_dropdown.set(current_skin)
            else:
                self.skin_dropdown.set(skins[0])
                
            self.launch_btn.configure(state="normal")
        else:
            self.skin_dropdown.configure(values=["No suites found!"])
            self.skin_dropdown.set("No suites found!")
            self.launch_btn.configure(state="disabled")

        num_monitors = get_connected_monitors()
        monitors = [f"Monitor {i}" for i in range(num_monitors)]
        self.monitor_dropdown.configure(values=monitors)
        self.monitor_dropdown.set(monitors[0])

    def open_skins_folder(self):
        # Uses standard Linux file manager command
        os.makedirs(SUITES_DIR, exist_ok=True)
        subprocess.Popen(["xdg-open", SUITES_DIR])

    def launch_suite(self):
        selected_skin = self.skin_dropdown.get()
        monitor_text = self.monitor_dropdown.get()
        
        if selected_skin == "No suites found!":
            return
            
        monitor_idx = int(monitor_text.split(" ")[1])

        try:
            os.makedirs(os.path.dirname(GLOBAL_CONFIG), exist_ok=True)
            with open(GLOBAL_CONFIG, "w") as f:
                f.write(f"[{selected_skin}]\nActive=1\n")
        except IOError as e:
            messagebox.showerror("Error", f"Config write failed:\n{e}")
            return

        kill_engine()
        time.sleep(0.5)
        
        os.chdir(BUILD_DIR)
        subprocess.Popen(
            ["./rainmeter-native", "-m", str(monitor_idx)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def kill_suite(self):
        kill_engine()

if __name__ == "__main__":
    app = RainmeterLauncher()
    app.mainloop()

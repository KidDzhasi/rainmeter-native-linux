# rainmeter-native

A lightweight, hardware-accelerated, Wayland-native rendering engine for Linux desktop environments. 

Unlike the legacy Windows client, `rainmeter-native` does not attempt to parse undocumented hacks or nested variables from older `.rmskin` files. Instead, it offers a clean, strict, and predictable INI syntax designed specifically for modern Linux systems.

## Getting Started: Building a Skin from Scratch

In `rainmeter-native`, a "Skin" is simply a folder containing an `.ini` file that defines your **Measures** (backend data) and **Meters** (frontend UI).

### 1. Folder Structure
Create a new directory for your suite inside the skins folder:
`~/.config/rainmeter-native/Skins/MyCustomSuite/`

Inside that folder, create your configuration file (e.g., `HUD.ini`).

### 2. The Global Rainmeter Block
Every `.ini` file must start with a base configuration block to tell the Wayland engine how fast to render:

```ini
[Rainmeter]
Update=1000

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

### 3. Adding Measures (The Data Layer)
Measures run silently in the background, polling the Linux filesystem (like /proc/stat and /sys/class/power_supply) for live telemetry.

Currently supported native measures:

Measure=CPU (Calculates overall CPU load)

Measure=Battery (Requires BatteryName=BAT0 or BAT1)

Ini, TOML
[MeasureCoreCPU]
Measure=CPU

[MeasureMainBattery]
Measure=Battery
BatteryName=BAT0

### 4. Adding Meters (The UI Layer)
Meters draw pixels to the screen using the NanoVG rendering pipeline. You can bind a Meter to a Measure using the MeasureName= key.

Supported Meter Types:

Shape: Draws vector geometry (Rectangle, Ellipse). Colors use standard R,G,B,A format.

String: Renders hardware-accelerated text. Use %1 to inject live data from a bound Measure.

Image: Loads .jpg or .png files directly into Wayland memory. (Place the image file in the same directory as your .ini).

### 5. Example: A Complete System HUD
Here is a complete, functioning example of a native widget. Paste this into your HUD.ini:

Ini, TOML
[Rainmeter]
Update=1000

; --- DATA BACKEND ---

[MeasureCoreCPU]
Measure=CPU

; --- FRONTEND UI ---

[MeterBackgroundPanel]
Meter=Shape
Shape=Rectangle 0,0,250,80,10 | Fill Color 15,20,30,220 | StrokeWidth 2 | Stroke Color 0,255,200,150
X=0
Y=0
LeftMouseUpAction=["notify-send 'System' 'HUD Clicked'"]

[MeterCPULabel]
Meter=String
MeasureName=MeasureCoreCPU
FontFace=Ubuntu
FontSize=16
FontWeight=700
FontColor=255,255,255,255
Text="CPU LOAD: %1%"
AntiAlias=1
X=15
Y=25

### 6. Activating the Skin
To load your new creation, edit your global layout file located at ~/.config/rainmeter-native/Rainmeter.ini and append your widget:

Ini, TOML
[MyCustomSuite]
Active=1
WindowX=(#SCREENAREAWIDTH# * 0.1)
WindowY=(#SCREENAREAHEIGHT# * 0.1)
Restart the rainmeter-native binary, and your custom Wayland widget will appear on the desktop!

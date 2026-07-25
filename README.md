# rainmeter-native

A native Linux rendering engine for Rainmeter skins. Built from the ground up with C++20, this project allows Linux users to parse, render, and interact with complex Rainmeter suites natively on their desktops without relying on WINE or Windows virtual machines.

## Features
* **Native Windowing:** Utilizes Wayland and LayerShell to draw true desktop widgets that sit underneath your active windows.
* **ActionTimer Animations:** Supports 60FPS fluid UI animations and physics.
* **Linux System Adapters:** Automatically intercepts Windows plugins (UsageMonitor, CoreTemp) and bridges them to native Linux `/proc` and `/sys` hardware metrics.
* **PipeWire Audio Visualizer:** Native `AudioLevel` FFT processing for music visualizers.

## Dependencies (Ubuntu / Pop!_OS)
Ensure you have the required build tools and libraries installed:
\`\`\`bash
sudo apt update
sudo apt install build-essential cmake libwayland-dev libpulse-dev libfftw3-dev
\`\`\`

## Build Instructions
\`\`\`bash
git clone https://github.com/KidDzhasi/rainmeter-native-linux.git
cd rainmeter-native-linux
cmake -B build
cmake --build build
\`\`\`

## Usage
Launch the daemon by passing the path to your desired `.ini` skin files:
\`\`\`bash
./build/rainmeter-native ~/.config/rainmeter-native/Skins/PopStats/Stats.ini
\`\`\`
